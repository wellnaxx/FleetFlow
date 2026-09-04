"""Heterogeneous registration and lookup for concrete outbox event codecs."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.eventing.outbox.errors import (
    DuplicateEventCodecError,
    EventCodecNotFoundError,
    EventCodecTypeMismatchError,
)
from src.shared.event import Event
from src.shared.json_types import JSONObject
from src.shared.validation import require_positive_int


class ErasedEventPayloadCodec(Protocol):
    """Type-erased codec stored in the heterogeneous registry."""

    @property
    def event_class(self) -> type[Event]:
        """Return the exact concrete event class handled by the codec."""
        ...

    @property
    def event_type(self) -> str:
        """Return the stable persisted event-type name."""
        ...

    @property
    def event_version(self) -> int:
        """Return the positive persisted contract version."""
        ...

    def encode(self, event: Event) -> JSONObject:
        """Encode an event after enforcing the erased runtime boundary."""
        ...

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> Event:
        """Decode and return an event through the erased boundary."""
        ...


class CodecAdapter[E: Event](ErasedEventPayloadCodec):
    """Erase a typed codec while retaining exact runtime type checks."""

    def __init__(self, event_class: type[E], codec: EventPayloadCodec[E]) -> None:
        """Wrap a codec whose generic event type matches ``event_class``.

        Raises:
            EventCodecTypeMismatchError: If the codec advertises a different
                concrete event class.
        """
        if codec.event_class is not event_class:
            raise EventCodecTypeMismatchError(
                f"Codec for {codec.event_class.__name__} cannot be registered as {event_class.__name__}."
            )
        self._event_class = event_class
        self._codec = codec

    @property
    def event_class(self) -> type[E]:
        """Return the wrapped concrete event class."""
        return self._event_class

    @property
    def event_type(self) -> str:
        """Return the wrapped codec's persisted event-type name."""
        return self._codec.event_type

    @property
    def event_version(self) -> int:
        """Return the wrapped codec's persisted contract version."""
        return self._codec.event_version

    def encode(self, event: Event) -> JSONObject:
        """Encode an event after requiring its exact registered type."""
        if type(event) is not self._event_class:
            raise EventCodecTypeMismatchError(
                f"Codec for {self._event_class.__name__} cannot encode {type(event).__name__}."
            )
        return self._codec.encode(event)

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> Event:
        """Decode an event and verify the concrete result type."""
        event = self._codec.decode(
            payload,
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
        )
        if type(event) is not self._event_class:
            raise EventCodecTypeMismatchError(
                f"Codec for {self._event_class.__name__} decoded {type(event).__name__}."
            )
        return event


class EventOutboxCodecRegistry:
    """Index erased codecs for live-event encoding and stored-event decoding."""

    def __init__(self) -> None:
        """Create an empty codec registry."""
        self._codecs_by_event_class: dict[type[Event], ErasedEventPayloadCodec] = {}
        self._codecs_by_identity: dict[tuple[str, int], ErasedEventPayloadCodec] = {}

    def register[E: Event](
        self,
        event_class: type[E],
        codec: EventPayloadCodec[E],
    ) -> None:
        """Register one codec under its event class and persisted identity.

        Both indexes are checked before either is modified, preventing a
        failed registration from leaving partial registry state.

        Args:
            event_class: Exact live event class used for encoding lookup.
            codec: Typed payload codec for that event class.

        Raises:
            DuplicateEventCodecError: If the class or ``(type, version)``
                identity is already registered.
            EventCodecTypeMismatchError: If ``codec.event_class`` differs
                from ``event_class``.
            TypeError: If ``codec.event_version`` is not an integer.
            ValueError: If ``codec.event_version`` is not positive.
        """
        event_version = require_positive_int(codec.event_version, "codec.event_version")
        identity = (codec.event_type, event_version)

        if event_class in self._codecs_by_event_class:
            raise DuplicateEventCodecError(f"Codec already registered for {event_class.__name__}.")

        if identity in self._codecs_by_identity:
            event_type, event_version = identity
            raise DuplicateEventCodecError(
                f"Codec already registered for event identity ({event_type!r}, {event_version})."
            )

        erased_codec = CodecAdapter(event_class, codec)

        self._codecs_by_event_class[event_class] = erased_codec
        self._codecs_by_identity[identity] = erased_codec

    def for_event(self, event: Event) -> ErasedEventPayloadCodec:
        """Resolve the codec registered for an event's exact runtime class.

        Raises:
            EventCodecNotFoundError: If the concrete event class is not
                registered.
        """
        try:
            return self._codecs_by_event_class[type(event)]
        except KeyError as exc:
            raise EventCodecNotFoundError(
                f"No codec registered for event type {type(event).__name__}."
            ) from exc

    def for_identity(self, event_type: str, event_version: int) -> ErasedEventPayloadCodec:
        """Resolve a codec from a persisted event type and version.

        Raises:
            EventCodecNotFoundError: If the persisted identity is not
                registered.
        """
        try:
            return self._codecs_by_identity[(event_type, event_version)]
        except KeyError as exc:
            raise EventCodecNotFoundError(
                f"No codec registered for event identity ({event_type!r}, {event_version})."
            ) from exc
