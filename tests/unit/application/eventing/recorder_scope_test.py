"""Tests for execution-local event-recorder scopes."""

import unittest
from dataclasses import dataclass
from datetime import datetime

from src.application.eventing.recorder_scope import (
    EventRecorderScope,
    bind_event_recorder_scope,
    get_event_recorder_scope,
    get_optional_event_recorder_scope,
    record_application_event,
    track_domain_recorder,
)
from src.application.events.base import ApplicationEvent
from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin
from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleApplicationEvent(ApplicationEvent):
    """Application event used by recorder-scope tests."""

    label: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleDomainEvent(DomainEvent):
    """Domain event used by recorder-scope tests."""

    label: str


class DomainRecorder(DomainEventRecorderMixin):
    """Domain recorder fake with explicit pending-event storage."""

    def __init__(self) -> None:
        self._pending_events: list[DomainEvent] = []

    def add(self, event: DomainEvent) -> None:
        """Append one domain event to the fake recorder."""
        self._record_event(event)


class EventRecorderScopeShould(unittest.TestCase):
    """Verify recorder storage, ordering, and context-local binding."""

    def test_start_with_itself_as_only_empty_event_recorder(self) -> None:
        scope = EventRecorderScope()

        self.assertEqual(scope.pending_events, ())
        self.assertEqual(scope.event_recorders(), (scope,))

    def test_preserve_application_event_recording_order_and_clear_only_its_buffer(self) -> None:
        scope = EventRecorderScope()
        first = self._application_event("first")
        second = self._application_event("second")
        domain_recorder = DomainRecorder()
        domain_event = self._domain_event("domain")
        domain_recorder.add(domain_event)
        scope.track_domain_recorder(domain_recorder)

        scope.record_application_event(first)
        scope.record_application_event(second)
        scope.clear_events()

        self.assertEqual(scope.pending_events, ())
        self.assertEqual(domain_recorder.pending_events, (domain_event,))
        self.assertEqual(scope.event_recorders(), (scope, domain_recorder))

    def test_track_domain_recorders_once_by_identity_in_registration_order(self) -> None:
        scope = EventRecorderScope()
        first = DomainRecorder()
        second = DomainRecorder()

        scope.track_domain_recorder(first)
        scope.track_domain_recorder(second)
        scope.track_domain_recorder(first)

        self.assertEqual(scope.event_recorders(), (scope, first, second))

    def test_require_bound_scope_from_strict_context_helpers(self) -> None:
        recorder = DomainRecorder()

        self.assertIsNone(get_optional_event_recorder_scope())
        with self.assertRaisesRegex(RuntimeError, "No event recorder scope is bound"):
            get_event_recorder_scope()
        with self.assertRaisesRegex(RuntimeError, "No event recorder scope is bound"):
            record_application_event(self._application_event("outside"))
        with self.assertRaisesRegex(RuntimeError, "No event recorder scope is bound"):
            track_domain_recorder(recorder)

    def test_bind_fresh_scope_and_route_module_helpers_to_it(self) -> None:
        event = self._application_event("scoped")
        recorder = DomainRecorder()

        with bind_event_recorder_scope() as scope:
            record_application_event(event)
            track_domain_recorder(recorder)

            self.assertIs(get_event_recorder_scope(), scope)
            self.assertEqual(scope.pending_events, (event,))
            self.assertEqual(scope.event_recorders(), (scope, recorder))

        self.assertIsNone(get_optional_event_recorder_scope())

    def test_nested_binding_isolate_events_and_restore_outer_scope(self) -> None:
        outer_event = self._application_event("outer")
        inner_event = self._application_event("inner")

        with bind_event_recorder_scope() as outer:
            record_application_event(outer_event)

            with bind_event_recorder_scope() as inner:
                record_application_event(inner_event)
                self.assertIs(get_event_recorder_scope(), inner)
                self.assertEqual(inner.pending_events, (inner_event,))

            self.assertIs(get_event_recorder_scope(), outer)
            self.assertEqual(outer.pending_events, (outer_event,))

        self.assertIsNone(get_optional_event_recorder_scope())

    def test_restore_previous_binding_when_managed_block_raises(self) -> None:
        with bind_event_recorder_scope() as outer:
            with (
                self.assertRaisesRegex(RuntimeError, "execution failed"),
                bind_event_recorder_scope(),
            ):
                raise RuntimeError("execution failed")

            self.assertIs(get_event_recorder_scope(), outer)

        self.assertIsNone(get_optional_event_recorder_scope())

    @staticmethod
    def _application_event(label: str) -> SampleApplicationEvent:
        return SampleApplicationEvent(occurred_at=datetime(2026, 8, 17, 12, 0), label=label)

    @staticmethod
    def _domain_event(label: str) -> SampleDomainEvent:
        return SampleDomainEvent(occurred_at=datetime(2026, 8, 17, 12, 0), label=label)


if __name__ == "__main__":
    unittest.main()
