"""Tests for the structured event logging handler."""

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.adapters.driven.events.structured_event_logging_handler import StructuredEventLoggingHandler
from src.application.enums.event_sources import EventSource
from src.application.eventing.envelope import EventActor, EventEnvelope
from src.shared.event import Event

_LOGGER_NAME = "src.adapters.driven.events.structured_event_logging_handler"


@dataclass(frozen=True, slots=True, kw_only=True)
class LoggedEvent(Event):
    """Test event used to verify logging output."""

    label: str


class StructuredEventLoggingHandlerShould(unittest.TestCase):
    def test_log_envelope_metadata_and_event_metadata(self) -> None:
        handler = StructuredEventLoggingHandler()
        envelope = EventEnvelope(
            event=LoggedEvent(
                event_id=UUID("11111111-1111-1111-1111-111111111111"),
                occurred_at=datetime(2026, 6, 25, 12, 0),
                recorded_at=datetime(2026, 6, 25, 12, 0, 1, tzinfo=UTC),
                label="created",
            ),
            source=EventSource.HTTP,
            correlation_id=UUID("22222222-2222-2222-2222-222222222222"),
            actor=EventActor(user_id=7, username="Admin"),
            causation_id=UUID("33333333-3333-3333-3333-333333333333"),
            envelope_id=UUID("44444444-4444-4444-4444-444444444444"),
        )

        with self.assertLogs(_LOGGER_NAME, level="INFO") as logs:
            handler.handle(envelope)

        self.assertEqual(len(logs.output), 1)
        log_line = logs.output[0]
        self.assertIn("Event published:", log_line)
        self.assertIn("event_type=LoggedEvent", log_line)
        self.assertIn("event_id=11111111-1111-1111-1111-111111111111", log_line)
        self.assertIn("occurred_at=2026-06-25T12:00:00", log_line)
        self.assertIn("recorded_at=2026-06-25T12:00:01+00:00", log_line)
        self.assertIn("envelope_id=44444444-4444-4444-4444-444444444444", log_line)
        self.assertIn("correlation_id=22222222-2222-2222-2222-222222222222", log_line)
        self.assertIn("causation_id=33333333-3333-3333-3333-333333333333", log_line)
        self.assertIn("source=HTTP", log_line)
        self.assertIn("actor_user_id=7", log_line)
        self.assertIn("actor_username=admin", log_line)

    def test_log_missing_actor_and_causation_as_none(self) -> None:
        handler = StructuredEventLoggingHandler()
        envelope = EventEnvelope(
            event=LoggedEvent(
                event_id=UUID("11111111-1111-1111-1111-111111111111"),
                occurred_at=datetime(2026, 6, 25, 12, 0),
                recorded_at=datetime(2026, 6, 25, 12, 0, 1, tzinfo=UTC),
                label="created",
            ),
            source=EventSource.SYSTEM,
            correlation_id=UUID("22222222-2222-2222-2222-222222222222"),
        )

        with self.assertLogs(_LOGGER_NAME, level="INFO") as logs:
            handler.handle(envelope)

        log_line = logs.output[0]
        self.assertIn("causation_id=None", log_line)
        self.assertIn("source=SYSTEM", log_line)
        self.assertIn("actor_user_id=None", log_line)
        self.assertIn("actor_username=None", log_line)
