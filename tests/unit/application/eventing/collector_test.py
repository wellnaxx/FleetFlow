"""Tests for collecting and publishing pending events."""

import unittest
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.application.enums.event_sources import EventSource
from src.application.eventing.collector import EventCollector
from src.application.eventing.context import EventContext
from src.application.eventing.current_context import bind_event_context
from src.application.eventing.envelope import EventEnvelope
from src.application.events.base import ApplicationEvent
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin
from src.domain.events.base import DomainEvent
from src.shared.event import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleApplicationEvent(ApplicationEvent):
    """Application event used by collector tests."""

    label: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleDomainEvent(DomainEvent):
    """Domain event used by collector tests."""

    label: str


class ApplicationRecorder(ApplicationEventRecorderMixin):
    """Application recorder fake with explicit event initialization."""

    def __init__(self) -> None:
        self._pending_events: list[ApplicationEvent] = []

    def add(self, event: ApplicationEvent) -> None:
        self._record_event(event)


class DomainRecorder(DomainEventRecorderMixin):
    """Domain recorder fake with explicit event initialization."""

    def __init__(self) -> None:
        self._pending_events: list[DomainEvent] = []

    def add(self, event: DomainEvent) -> None:
        self._record_event(event)


class RecordingPublisher:
    """Publisher fake that records the envelopes it receives."""

    def __init__(self) -> None:
        self.envelopes: tuple[EventEnvelope[Event], ...] = ()

    def publish(self, envelope: EventEnvelope[Event]) -> None:
        self.publish_all((envelope,))

    def publish_all(self, envelopes: tuple[EventEnvelope[Event], ...]) -> None:
        self.envelopes = envelopes


class FailingPublisher:
    """Publisher fake that fails while retaining call evidence."""

    def __init__(self) -> None:
        self.called = False

    def publish(self, envelope: EventEnvelope[Event]) -> None:
        self.publish_all((envelope,))

    def publish_all(self, envelopes: tuple[EventEnvelope[Event], ...]) -> None:
        del envelopes
        self.called = True
        raise RuntimeError("publish failed")


class EventCollectorShould(unittest.TestCase):
    def test_publish_pending_events_in_recorder_and_event_order_then_clear(self) -> None:
        publisher = RecordingPublisher()
        collector = EventCollector(publisher)
        application_recorder = ApplicationRecorder()
        domain_recorder = DomainRecorder()
        first = SampleApplicationEvent(occurred_at=self._occurred_at(), label="first")
        second = SampleApplicationEvent(occurred_at=self._occurred_at(), label="second")
        third = SampleDomainEvent(occurred_at=self._occurred_at(), label="third")
        application_recorder.add(first)
        application_recorder.add(second)
        domain_recorder.add(third)

        with bind_event_context(self._context()):
            collector.drain((application_recorder, domain_recorder))

        self.assertEqual(tuple(envelope.event for envelope in publisher.envelopes), (first, second, third))
        self.assertEqual(application_recorder.pending_events, ())
        self.assertEqual(domain_recorder.pending_events, ())

    def test_bind_current_event_context_to_published_envelopes(self) -> None:
        publisher = RecordingPublisher()
        collector = EventCollector(publisher)
        recorder = ApplicationRecorder()
        recorder.add(SampleApplicationEvent(occurred_at=self._occurred_at(), label="event"))

        context = self._context()
        with bind_event_context(context):
            collector.drain((recorder,))

        (envelope,) = publisher.envelopes
        self.assertEqual(envelope.source, context.source)
        self.assertEqual(envelope.correlation_id, context.correlation_id)
        self.assertEqual(envelope.actor, context.actor)
        self.assertEqual(envelope.causation_id, context.causation_id)

    def test_not_publish_when_no_recorders_have_pending_events(self) -> None:
        publisher = RecordingPublisher()
        collector = EventCollector(publisher)

        with bind_event_context(self._context()):
            collector.drain((ApplicationRecorder(), DomainRecorder()))

        self.assertEqual(publisher.envelopes, ())

    def test_accept_generator_of_recorders_and_clear_after_publish(self) -> None:
        publisher = RecordingPublisher()
        collector = EventCollector(publisher)
        recorder = ApplicationRecorder()
        recorder.add(SampleApplicationEvent(occurred_at=self._occurred_at(), label="event"))

        with bind_event_context(self._context()):
            collector.drain(recorder for recorder in (recorder,))

        self.assertEqual(len(publisher.envelopes), 1)
        self.assertEqual(recorder.pending_events, ())

    def test_reject_duplicate_recorder_instances(self) -> None:
        collector = EventCollector(RecordingPublisher())
        recorder = ApplicationRecorder()
        recorder.add(SampleApplicationEvent(occurred_at=self._occurred_at(), label="event"))

        with (
            bind_event_context(self._context()),
            self.assertRaisesRegex(ValueError, "same event recorder"),
        ):
            collector.drain((recorder, recorder))

        self.assertEqual(len(recorder.pending_events), 1)

    def test_preserve_pending_events_when_publish_fails(self) -> None:
        publisher = FailingPublisher()
        collector = EventCollector(publisher)
        recorder = ApplicationRecorder()
        event = SampleApplicationEvent(occurred_at=self._occurred_at(), label="event")
        recorder.add(event)

        with (
            bind_event_context(self._context()),
            self.assertRaisesRegex(RuntimeError, "publish failed"),
        ):
            collector.drain((recorder,))

        self.assertTrue(publisher.called)
        self.assertEqual(recorder.pending_events, (event,))

    @staticmethod
    def _occurred_at() -> datetime:
        return datetime(2026, 6, 26, 12, 0)

    @staticmethod
    def _context() -> EventContext:
        return EventContext(
            correlation_id=UUID("11111111-1111-1111-1111-111111111111"),
            causation_id=UUID("22222222-2222-2222-2222-222222222222"),
            source=EventSource.CLI,
        )
