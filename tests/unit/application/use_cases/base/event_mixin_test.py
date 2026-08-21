"""Tests for transitional application-event recording behavior."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from src.application.eventing.recorder_scope import bind_event_recorder_scope
from src.application.events.base import ApplicationEvent
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin

if TYPE_CHECKING:
    from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleApplicationEvent(ApplicationEvent):
    """Application event used by recording-mixin tests."""

    label: str


class ApplicationRecorder(ApplicationEventRecorderMixin):
    """Legacy-capable application recorder fake."""

    def __init__(self) -> None:
        self._pending_events: list[ApplicationEvent] = []


class DomainRecorder(DomainEventRecorderMixin):
    """Domain recorder fake used to verify scoped registration."""

    def __init__(self) -> None:
        self._pending_events: list[DomainEvent] = []


class ApplicationEventRecorderMixinShould(unittest.TestCase):
    """Verify mutually exclusive scoped and legacy event destinations."""

    def test_record_on_use_case_when_no_scope_is_bound(self) -> None:
        recorder = ApplicationRecorder()
        event = self._event("legacy")

        recorder.record_event(event)

        self.assertEqual(recorder.pending_events, (event,))

    def test_record_in_scope_without_duplicating_on_use_case(self) -> None:
        recorder = ApplicationRecorder()
        event = self._event("scoped")

        with bind_event_recorder_scope() as scope:
            recorder.record_event(event)

            self.assertEqual(scope.pending_events, (event,))
            self.assertEqual(recorder.pending_events, ())

    def test_track_domain_recorder_registers_once_in_active_scope(self) -> None:
        recorder = ApplicationRecorder()
        domain_recorder = DomainRecorder()

        with bind_event_recorder_scope() as scope:
            recorder.track_domain_recorder(domain_recorder)
            recorder.track_domain_recorder(domain_recorder)

            self.assertEqual(scope.event_recorders(), (scope, domain_recorder))

    def test_track_domain_recorder_is_no_op_without_scope(self) -> None:
        recorder = ApplicationRecorder()

        recorder.track_domain_recorder(DomainRecorder())

    @staticmethod
    def _event(label: str) -> SampleApplicationEvent:
        return SampleApplicationEvent(occurred_at=datetime(2026, 8, 17, 12, 0), label=label)


if __name__ == "__main__":
    unittest.main()
