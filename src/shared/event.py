"""Shared metadata for immutable system events."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """Base metadata shared by immutable system events.

    Attributes:
        event_id: Unique identifier for this event instance.
        occurred_at: Business time at which the represented fact occurred.
        recorded_at: UTC time at which FleetFlow recorded the event.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
