"""Typed contracts for encoding and decoding concrete event payloads."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.shared.event import Event
from src.shared.json_types import JSONObject


class EventPayloadDecoder[E: Event](Protocol):
    """Decode one persisted payload version into the current event class.

    ``event_version`` identifies the input payload, not necessarily the output
    event's current version. Historical decoders explicitly supply or transform
    fields required by the current class; the registry never invents defaults.
    Implementations must preserve supplied metadata and not mutate the payload.
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


class EventPayloadCodec[E: Event](EventPayloadDecoder[E], Protocol):
    """Encode and decode the current contract of one concrete event class.

    ``event_version`` must equal ``event_class.event_version``. Only
    event-specific fields belong in the payload; metadata stays in dedicated
    outbox columns. Decoders enforce payload field types and invariants.

    Direct encoding is a projection, not a validation boundary. Durable writes
    must use the registry adapter, which validates JSON safety and checks that
    decoding the emitted payload reproduces the original dataclass event.
    Codecs must be deterministic and side-effect free: this check runs the
    decoder on every encode. New incompatible payload shapes need a new version
    and an explicit historical decoder when old rows must remain replayable.
    """

    def encode(self, event: E) -> JSONObject:
        """Project event-specific fields as a JSON object, without metadata."""
        ...
