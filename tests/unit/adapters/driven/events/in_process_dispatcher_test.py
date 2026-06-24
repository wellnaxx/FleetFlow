"""Tests for synchronous in-process event dispatch."""

import unittest
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from src.adapters.driven.events.in_process_dispatcher import InProcessEventDispatcher
from src.application.enums.event_sources import EventSource
from src.application.eventing.envelope import EventEnvelope
from src.shared.event import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class FirstEvent(Event):
    """Test event used to verify exact-type dispatch."""

    label: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SecondEvent(Event):
    """Distinct test event used to verify non-matching subscriptions."""

    label: str


class RecordingHandler[E: Event]:
    """Test handler that records every envelope it receives."""

    def __init__(self, calls: list[str] | None = None, label: str | None = None) -> None:
        self.envelopes: list[EventEnvelope[E]] = []
        self._calls = calls
        self._label = label

    def handle(self, envelope: EventEnvelope[E]) -> None:
        self.envelopes.append(envelope)
        if self._calls is not None and self._label is not None:
            self._calls.append(self._label)


class FailingHandler:
    """Test handler that aborts dispatch with a configured error."""

    def __init__(self) -> None:
        self.calls = 0

    def handle(self, envelope: EventEnvelope[FirstEvent]) -> None:
        del envelope
        self.calls += 1
        raise RuntimeError("handler failed")


class SubscribingHandler:
    """Test handler that registers another handler while handling an event."""

    def __init__(
        self,
        dispatcher: InProcessEventDispatcher,
        handler: RecordingHandler[FirstEvent],
    ) -> None:
        self._dispatcher = dispatcher
        self._handler = handler

    def handle(self, envelope: EventEnvelope[FirstEvent]) -> None:
        del envelope
        self._dispatcher.subscribe(FirstEvent, self._handler)


class InProcessEventDispatcherShould(unittest.TestCase):
    def test_dispatch_matching_event_to_registered_handler(self) -> None:
        dispatcher = InProcessEventDispatcher()
        handler = RecordingHandler[FirstEvent]()
        envelope = self._envelope(FirstEvent(occurred_at=self._occurred_at(), label="first"))
        dispatcher.subscribe(FirstEvent, handler)

        dispatcher.publish(envelope)

        self.assertEqual(handler.envelopes, [envelope])

    def test_not_dispatch_event_to_handler_registered_for_different_type(self) -> None:
        dispatcher = InProcessEventDispatcher()
        handler = RecordingHandler[FirstEvent]()
        dispatcher.subscribe(FirstEvent, handler)

        dispatcher.publish(self._envelope(SecondEvent(occurred_at=self._occurred_at(), label="second")))

        self.assertEqual(handler.envelopes, [])

    def test_dispatch_handlers_in_subscription_order(self) -> None:
        dispatcher = InProcessEventDispatcher()
        calls: list[str] = []
        first_handler = RecordingHandler[FirstEvent](calls, "first")
        second_handler = RecordingHandler[FirstEvent](calls, "second")
        dispatcher.subscribe(FirstEvent, first_handler)
        dispatcher.subscribe(FirstEvent, second_handler)

        dispatcher.publish(self._envelope(FirstEvent(occurred_at=self._occurred_at(), label="event")))

        self.assertEqual(calls, ["first", "second"])

    def test_ignore_event_with_no_registered_handlers(self) -> None:
        dispatcher = InProcessEventDispatcher()

        dispatcher.publish(self._envelope(FirstEvent(occurred_at=self._occurred_at(), label="event")))

    def test_publish_batch_in_supplied_order(self) -> None:
        dispatcher = InProcessEventDispatcher()
        handler = RecordingHandler[FirstEvent]()
        first = self._envelope(FirstEvent(occurred_at=self._occurred_at(), label="first"))
        second = self._envelope(FirstEvent(occurred_at=self._occurred_at(), label="second"))
        dispatcher.subscribe(FirstEvent, handler)

        dispatcher.publish_all((first, second))

        self.assertEqual(handler.envelopes, [first, second])

    def test_propagate_handler_failure_and_stop_batch(self) -> None:
        dispatcher = InProcessEventDispatcher()
        failing_handler = FailingHandler()
        recording_handler = RecordingHandler[FirstEvent]()
        first = self._envelope(FirstEvent(occurred_at=self._occurred_at(), label="first"))
        second = self._envelope(FirstEvent(occurred_at=self._occurred_at(), label="second"))
        dispatcher.subscribe(FirstEvent, failing_handler)
        dispatcher.subscribe(FirstEvent, recording_handler)

        with self.assertRaisesRegex(RuntimeError, "handler failed"):
            dispatcher.publish_all((first, second))

        self.assertEqual(failing_handler.calls, 1)
        self.assertEqual(recording_handler.envelopes, [])

    def test_not_dispatch_handler_subscribed_during_current_publication(self) -> None:
        dispatcher = InProcessEventDispatcher()
        late_handler = RecordingHandler[FirstEvent]()
        dispatcher.subscribe(FirstEvent, SubscribingHandler(dispatcher, late_handler))
        envelope = self._envelope(FirstEvent(occurred_at=self._occurred_at(), label="event"))

        dispatcher.publish(envelope)

        self.assertEqual(late_handler.envelopes, [])

    @staticmethod
    def _occurred_at() -> datetime:
        return datetime(2026, 6, 24, 12, 0)

    @staticmethod
    def _envelope[E: Event](event: E) -> EventEnvelope[E]:
        return EventEnvelope(
            event=event,
            source=EventSource.CLI,
            correlation_id=uuid4(),
        )
