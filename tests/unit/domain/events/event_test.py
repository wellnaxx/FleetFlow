"""Tests for shared event metadata and concrete domain event shapes."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.domain.events.base import DomainEvent
from src.domain.events.customer_events import CustomerCreated
from src.domain.events.route_events import RouteCompleted


def test_domain_event_uses_explicit_occurrence_time_and_generated_metadata() -> None:
    occurred_at = datetime(2026, 6, 7, 12, 30)

    event = RouteCompleted(route_id=17, occurred_at=occurred_at)

    assert isinstance(event, DomainEvent)
    assert event.route_id == 17
    assert event.occurred_at is occurred_at
    assert isinstance(event.event_id, UUID)
    assert event.recorded_at.tzinfo is UTC


def test_domain_events_receive_unique_ids() -> None:
    occurred_at = datetime(2026, 6, 7, 12, 30)

    first = RouteCompleted(route_id=17, occurred_at=occurred_at)
    second = RouteCompleted(route_id=17, occurred_at=occurred_at)

    assert first.event_id != second.event_id


def test_domain_event_metadata_can_be_restored_explicitly() -> None:
    occurred_at = datetime(2026, 6, 7, 12, 30)
    recorded_at = datetime(2026, 6, 7, 9, 30, tzinfo=UTC)
    event_id = UUID("8e10f550-9b6f-4687-bc6e-7596508abc6a")

    event = CustomerCreated(
        customer_id=3,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        event_id=event_id,
    )

    assert event.event_id == event_id
    assert event.occurred_at == occurred_at
    assert event.recorded_at == recorded_at


def test_domain_events_are_immutable() -> None:
    event = RouteCompleted(
        route_id=17,
        occurred_at=datetime(2026, 6, 7, 12, 30),
    )

    with pytest.raises(FrozenInstanceError):
        event.route_id = 18  # type: ignore[reportAttributeAccessIssue]


def test_domain_event_fields_are_keyword_only() -> None:
    with pytest.raises(TypeError):
        RouteCompleted(17, datetime(2026, 6, 7, 12, 30))  # type: ignore[misc]
