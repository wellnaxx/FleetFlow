"""Tests for scoped event drainage around message execution."""

import unittest
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from src.application.enums.event_sources import EventSource
from src.application.eventing.collector import EventCollector, EventRecorder
from src.application.eventing.context import EventContext
from src.application.eventing.current_context import bind_event_context
from src.application.eventing.envelope import EventEnvelope
from src.application.eventing.recorder_scope import (
    EventRecorderScope,
    bind_event_recorder_scope,
    get_event_recorder_scope,
    get_optional_event_recorder_scope,
    record_application_event,
    track_domain_recorder,
)
from src.application.events.base import ApplicationEvent
from src.application.messaging.executors.event_draining import EventDrainingExecutor
from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin
from src.domain.events.base import DomainEvent
from src.shared.event import Event


@dataclass(frozen=True, slots=True)
class ExampleMessage:
    """Message used to exercise the generic executor."""

    value: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleApplicationEvent(ApplicationEvent):
    """Application event emitted by executor-test delegates."""

    label: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleDomainEvent(DomainEvent):
    """Domain event emitted by an executor-test recorder."""

    label: str


class DomainRecorder(DomainEventRecorderMixin):
    """Domain recorder fake with explicit pending-event storage."""

    def __init__(self) -> None:
        self._pending_events: list[DomainEvent] = []

    def add(self, event: DomainEvent) -> None:
        """Append one domain event to the recorder."""
        self._record_event(event)


class CallbackExecutor:
    """Delegate execution to a callback while retaining received messages."""

    def __init__(self, callback: Callable[[ExampleMessage], object]) -> None:
        self._callback = callback
        self.messages: list[ExampleMessage] = []

    def execute(self, message: ExampleMessage) -> object:
        """Record and execute one message."""
        self.messages.append(message)
        return self._callback(message)


class RecordingPublisher:
    """Publisher fake retaining every successfully published envelope."""

    def __init__(self) -> None:
        self.envelopes: tuple[EventEnvelope[Event], ...] = ()

    def publish(self, envelope: EventEnvelope[Event]) -> None:
        """Publish one envelope through the batch implementation."""
        self.publish_all((envelope,))

    def publish_all(self, envelopes: tuple[EventEnvelope[Event], ...]) -> None:
        """Retain one complete publication batch."""
        self.envelopes = envelopes


class RecordingCollector(EventCollector):
    """Collector test double that captures recorder tuples and may fail."""

    def __init__(self, error: Exception | None = None) -> None:
        super().__init__(RecordingPublisher())
        self.calls: list[tuple[EventRecorder, ...]] = []
        self.error = error

    def drain(self, recorders: Iterable[EventRecorder]) -> None:
        """Capture materialized recorders and raise the configured failure."""
        self.calls.append(tuple(recorders))
        if self.error is not None:
            raise self.error


class EventDrainingExecutorShould(unittest.TestCase):
    """Verify scoped execution, drainage, and exception precedence."""

    def test_pass_message_return_exact_result_and_drain_once(self) -> None:
        expected = object()
        delegate = CallbackExecutor(lambda message: expected)
        collector = RecordingCollector()
        executor = EventDrainingExecutor(delegate, collector)
        message = ExampleMessage(value=7)

        result = executor.execute(message)

        self.assertIs(result, expected)
        self.assertEqual(delegate.messages, [message])
        self.assertEqual(len(collector.calls), 1)
        self.assertEqual(len(collector.calls[0]), 1)
        self.assertIsNone(get_optional_event_recorder_scope())

    def test_drain_application_and_deduplicated_domain_recorders_in_order(self) -> None:
        application_event = self._application_event("application")
        first_domain = DomainRecorder()
        second_domain = DomainRecorder()
        first_event = self._domain_event("first")
        second_event = self._domain_event("second")
        first_domain.add(first_event)
        second_domain.add(second_event)

        def action(message: ExampleMessage) -> object:
            del message
            record_application_event(application_event)
            track_domain_recorder(first_domain)
            track_domain_recorder(second_domain)
            track_domain_recorder(first_domain)
            return object()

        collector = RecordingCollector()
        executor = EventDrainingExecutor(CallbackExecutor(action), collector)

        executor.execute(ExampleMessage(value=1))

        scope, first, second = collector.calls[0]
        self.assertEqual(scope.pending_events, (application_event,))
        self.assertIs(first, first_domain)
        self.assertIs(second, second_domain)
        self.assertEqual(first.pending_events, (first_event,))
        self.assertEqual(second.pending_events, (second_event,))

    def test_create_fresh_scope_for_each_execution(self) -> None:
        collector = RecordingCollector()
        executor = EventDrainingExecutor(CallbackExecutor(lambda message: message.value), collector)

        executor.execute(ExampleMessage(value=1))
        executor.execute(ExampleMessage(value=2))

        first_scope = collector.calls[0][0]
        second_scope = collector.calls[1][0]
        self.assertIsNot(first_scope, second_scope)

    def test_publish_application_then_domain_events_and_clear_both_recorders(self) -> None:
        publisher = RecordingPublisher()
        collector = EventCollector(publisher)
        application_event = self._application_event("application")
        domain_recorder = DomainRecorder()
        domain_event = self._domain_event("domain")
        domain_recorder.add(domain_event)

        def action(message: ExampleMessage) -> object:
            del message
            record_application_event(application_event)
            track_domain_recorder(domain_recorder)
            return get_event_recorder_scope()

        executor = EventDrainingExecutor(CallbackExecutor(action), collector)

        with bind_event_context(
            EventContext(
                correlation_id=UUID("11111111-1111-1111-1111-111111111111"),
                source=EventSource.CLI,
            )
        ):
            scope = cast(EventRecorderScope, executor.execute(ExampleMessage(value=1)))

        self.assertEqual(
            tuple(envelope.event for envelope in publisher.envelopes),
            (application_event, domain_event),
        )
        self.assertEqual(scope.pending_events, ())
        self.assertEqual(domain_recorder.pending_events, ())

    def test_restore_outer_scope_after_nested_execution(self) -> None:
        collector = RecordingCollector()

        def action(message: ExampleMessage) -> object:
            del message
            return get_event_recorder_scope()

        executor = EventDrainingExecutor(CallbackExecutor(action), collector)

        with bind_event_recorder_scope() as outer:
            inner = executor.execute(ExampleMessage(value=1))
            self.assertIsNot(inner, outer)
            self.assertIs(get_event_recorder_scope(), outer)

        self.assertIsNone(get_optional_event_recorder_scope())

    def test_drain_failure_events_then_reraise_identical_delegate_exception(self) -> None:
        expected_error = RuntimeError("delegate failed")
        event = self._application_event("rejected")

        def action(message: ExampleMessage) -> object:
            del message
            record_application_event(event)
            raise expected_error

        collector = RecordingCollector()
        executor = EventDrainingExecutor(CallbackExecutor(action), collector)

        with self.assertRaises(RuntimeError) as raised:
            executor.execute(ExampleMessage(value=1))

        self.assertIs(raised.exception, expected_error)
        self.assertEqual(len(collector.calls), 1)
        self.assertEqual(collector.calls[0][0].pending_events, (event,))
        self.assertIsNone(get_optional_event_recorder_scope())

    def test_propagate_publication_failure_after_successful_execution(self) -> None:
        publish_error = RuntimeError("publication failed")
        collector = RecordingCollector(error=publish_error)
        executor = EventDrainingExecutor(CallbackExecutor(lambda message: message.value), collector)

        with self.assertRaises(RuntimeError) as raised:
            executor.execute(ExampleMessage(value=1))

        self.assertIs(raised.exception, publish_error)
        self.assertEqual(len(collector.calls), 1)
        self.assertIsNone(get_optional_event_recorder_scope())

    def test_log_failure_path_publication_error_and_preserve_delegate_exception(self) -> None:
        delegate_error = ValueError("delegate failed")
        publish_error = RuntimeError("publication failed")

        def action(message: ExampleMessage) -> object:
            del message
            raise delegate_error

        collector = RecordingCollector(error=publish_error)
        executor = EventDrainingExecutor(CallbackExecutor(action), collector)

        with (
            self.assertLogs(
                "src.application.messaging.executors.event_draining",
                level="ERROR",
            ) as logs,
            self.assertRaises(ValueError) as raised,
        ):
            executor.execute(ExampleMessage(value=1))

        self.assertIs(raised.exception, delegate_error)
        self.assertEqual(len(collector.calls), 1)
        self.assertTrue(any("Failed to publish pending events" in entry for entry in logs.output))
        self.assertIsNone(get_optional_event_recorder_scope())

    @staticmethod
    def _application_event(label: str) -> SampleApplicationEvent:
        return SampleApplicationEvent(occurred_at=datetime(2026, 8, 17, 12, 0), label=label)

    @staticmethod
    def _domain_event(label: str) -> SampleDomainEvent:
        return SampleDomainEvent(occurred_at=datetime(2026, 8, 17, 12, 0), label=label)


if __name__ == "__main__":
    unittest.main()
