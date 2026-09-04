"""Typed contracts for encoding and decoding concrete event payloads."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.shared.event import Event
from src.shared.json_types import JSONObject


class EventPayloadCodec[E: Event](Protocol):
    """Encode one concrete event contract to and from a JSON payload.

    Implementations handle only event-specific fields. Universal event and
    envelope metadata remains in dedicated outbox columns.
    """

    @property
    def event_class(self) -> type[E]:
        """Return the exact concrete event class handled by this codec."""
        ...

    @property
    def event_type(self) -> str:
        """Return the stable persisted event-type name."""
        ...

    @property
    def event_version(self) -> int:
        """Return the positive persisted contract version."""
        ...

    def encode(self, event: E) -> JSONObject:
        """Encode event-specific fields as a JSON object."""
        ...

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> E:
        """Reconstruct an event from its payload and universal metadata."""
        ...
