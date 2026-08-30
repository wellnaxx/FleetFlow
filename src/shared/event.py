"""Shared metadata for immutable system events."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID, uuid4

from src.shared.validation import require_naive_datetime, require_utc_datetime, require_uuid


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """Base metadata shared by immutable system events.

    Attributes:
        event_version: Version of the concrete event's persisted contract.
        event_id: Unique identifier for this event instance.
        occurred_at: Naive app-local business time at which the represented
            fact occurred.
        recorded_at: UTC time at which FleetFlow recorded the event.
    """

    event_version: ClassVar[int] = 1

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate event identity and its two intentional time domains.

        Raises:
            TypeError: If event metadata has an incompatible runtime type.
            ValueError: If occurrence time is aware or recording time is not
                represented in UTC.
        """
        require_uuid(self.event_id, "event_id")
        require_naive_datetime(self.occurred_at, "occurred_at")
        require_utc_datetime(self.recorded_at, "recorded_at")
