"""Tests for shared event metadata and concrete domain event shapes."""

import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

from src.domain.enums.route_status import RouteStatus
from src.domain.events.base import DomainEvent
from src.domain.events.customer_events import CustomerCreated
from src.domain.events.route_events import RouteCompleted


class DomainEventShould(unittest.TestCase):
    def test_use_explicit_occurrence_time_and_generated_metadata(self) -> None:
        occurred_at = datetime(2026, 6, 7, 12, 30)

        event = _route_completed(occurred_at)

        self.assertIsInstance(event, DomainEvent)
        self.assertEqual(event.route_id, 17)
        self.assertIs(event.occurred_at, occurred_at)
        self.assertIsInstance(event.event_id, UUID)
        self.assertIs(event.recorded_at.tzinfo, UTC)

    def test_receive_unique_ids(self) -> None:
        occurred_at = datetime(2026, 6, 7, 12, 30)

        first = _route_completed(occurred_at)
        second = _route_completed(occurred_at)

        self.assertNotEqual(first.event_id, second.event_id)

    def test_restore_metadata_explicitly(self) -> None:
        occurred_at = datetime(2026, 6, 7, 12, 30)
        recorded_at = datetime(2026, 6, 7, 9, 30, tzinfo=UTC)
        event_id = UUID("8e10f550-9b6f-4687-bc6e-7596508abc6a")

        event = CustomerCreated(
            customer_id=3,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            event_id=event_id,
        )

        self.assertEqual(event.event_id, event_id)
        self.assertEqual(event.occurred_at, occurred_at)
        self.assertEqual(event.recorded_at, recorded_at)

    def test_be_immutable(self) -> None:
        event = _route_completed(datetime(2026, 6, 7, 12, 30))

        with self.assertRaises(FrozenInstanceError):
            event.route_id = 18  # type: ignore[reportAttributeAccessIssue]

    def test_require_keyword_only_fields(self) -> None:
        with self.assertRaises(TypeError):
            RouteCompleted(17, datetime(2026, 6, 7, 12, 30))  # type: ignore[misc]

    def test_expose_concrete_event_contract_version(self) -> None:
        event = _route_completed(datetime(2026, 6, 7, 12, 30))

        self.assertEqual(event.event_version, 2)

    def test_require_naive_occurrence_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "occurred_at must be timezone-naive"):
            _route_completed(datetime(2026, 6, 7, 12, 30, tzinfo=UTC))

    def test_require_utc_recording_time(self) -> None:
        for recorded_at in (
            datetime(2026, 6, 7, 12, 30),
            datetime(2026, 6, 7, 12, 30, tzinfo=timezone(timedelta(hours=3))),
        ):
            with self.subTest(recorded_at=recorded_at), self.assertRaises(ValueError):
                CustomerCreated(
                    customer_id=3,
                    occurred_at=datetime(2026, 6, 7, 12, 30),
                    recorded_at=recorded_at,
                )


def _route_completed(occurred_at: datetime) -> RouteCompleted:
    """Build a valid enriched route-completion event for metadata tests."""
    return RouteCompleted(
        route_id=17,
        previous_status=RouteStatus.IN_PROGRESS,
        new_status=RouteStatus.COMPLETED,
        departure_time=datetime(2026, 6, 7, 8, 0),
        expected_completion_time=occurred_at,
        occurred_at=occurred_at,
    )
