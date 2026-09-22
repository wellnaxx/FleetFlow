"""Heterogeneous registration and lookup for concrete outbox event codecs."""

from copy import deepcopy
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec, EventPayloadDecoder
from src.application.eventing.outbox.errors import (
    DuplicateEventCodecError,
    EventCodecContractError,
    EventCodecNotFoundError,
    EventCodecTypeMismatchError,
    EventCodecVersionMismatchError,
)
from src.shared.event import Event
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object
from src.shared.validation import (
    require_naive_datetime,
    require_non_empty_str,
    require_positive_int,
    require_utc_datetime,
    require_uuid,
)


class ErasedEventPayloadDecoder(Protocol):
    """Type-erased read contract resolved by persisted payload identity."""

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


class ErasedEventPayloadCodec(ErasedEventPayloadDecoder, Protocol):
    """Current read/write contract resolved by the exact live event class."""

    def encode(self, event: Event) -> JSONObject:
        """Return a JSON-safe payload that reproduces the event on decoding."""
        ...


class DecoderAdapter[E: Event](ErasedEventPayloadDecoder):
    """Erase a decoder's type while preserving its validated wire identity.

    A historical decoder may reconstruct a newer event class. It must perform
    that transformation explicitly and preserve the original event metadata.
    """

    def __init__(self, event_class: type[E], codec: EventPayloadDecoder[E]) -> None:
        """Capture a decoder's immutable registration identity.

        Raises:
            EventCodecTypeMismatchError: If the codec advertises a different
                concrete event class.
            TypeError: If an identity field has an invalid runtime type.
            ValueError: If the name is blank/padded or a version is not positive.
        """
        if codec.event_class is not event_class:
            raise EventCodecTypeMismatchError(
                f"Codec for {codec.event_class.__name__} cannot be registered as {event_class.__name__}."
            )
        self._event_class = event_class
        self._decoder = codec
        self._event_type = _require_event_type(codec.event_type)
        self._event_version = require_positive_int(codec.event_version, "codec.event_version")
        require_positive_int(event_class.event_version, "event_class.event_version")

    @property
    def event_class(self) -> type[E]:
        """Return the wrapped concrete event class."""
        return self._event_class

    @property
    def event_type(self) -> str:
        """Return the persisted event-type name captured at registration."""
        return self._event_type

    @property
    def event_version(self) -> int:
        """Return the input payload version captured at registration."""
        return self._event_version

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> Event:
        """Validate wire data and reconstruct the current event without mutation.

        Args:
            payload: Event-specific JSON object for this decoder's wire version.
            event_id: Original event identifier, preserved during replay.
            occurred_at: Original naive business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            The exact registered event class, including for historical inputs.

        Raises:
            TypeError: If JSON or metadata types are invalid.
            ValueError: If metadata or decoder-specific field invariants fail.
            EventCodecTypeMismatchError: If the decoder returns another class.
            EventCodecContractError: If decoding changes the supplied metadata.

        Decoder-specific validation errors propagate unchanged. The decoder
        receives a deep copy so nested payloads remain owned by the caller.
        """
        validated = require_json_object(payload, "payload")
        require_uuid(event_id, "event_id")
        require_naive_datetime(occurred_at, "occurred_at")
        require_utc_datetime(recorded_at, "recorded_at")
        event = self._decoder.decode(
            deepcopy(validated),
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
        )
        if type(event) is not self._event_class:
            raise EventCodecTypeMismatchError(
                f"Codec for {self._event_class.__name__} decoded {type(event).__name__}."
            )
        if (event.event_id, event.occurred_at, event.recorded_at) != (event_id, occurred_at, recorded_at):
            raise EventCodecContractError(f"Decoder for {self._event_type} changed event metadata.")
        return event


class CodecAdapter[E: Event](DecoderAdapter[E], ErasedEventPayloadCodec):
    """Validate current payloads at the boundary used for durable writes."""

    def __init__(self, event_class: type[E], codec: EventPayloadCodec[E]) -> None:
        """Wrap a current codec, rejecting a version different from its class.

        Raises:
            EventCodecVersionMismatchError: If the wire version is not current.
            EventCodecTypeMismatchError: If the codec advertises another class.
            TypeError: If an identity field has an invalid runtime type.
            ValueError: If the name is blank/padded or a version is not positive.
        """
        super().__init__(event_class, codec)
        if self.event_version != event_class.event_version:
            raise EventCodecVersionMismatchError(
                f"Current codec for {event_class.__name__} must use version {event_class.event_version}, "
                f"got {self.event_version}."
            )
        self._codec = codec

    def encode(self, event: Event) -> JSONObject:
        """Validate JSON safety and lossless replay before returning a payload.

        Args:
            event: Exact current event class associated with this adapter.

        Returns:
            JSON-safe event-specific fields validated by the matching decoder.

        Raises:
            EventCodecTypeMismatchError: If the event or decoded class differs.
            EventCodecVersionMismatchError: If the event's version has changed.
            EventCodecContractError: If the round trip changes event data.
            TypeError: If encoded JSON or decoded field types are invalid.
            ValueError: If a decoder's field invariants fail.

        This intentionally runs the decoder once per encode, reusing its field
        validation instead of duplicating it in every encoder. Event dataclass
        equality supplies the losslessness check; metadata is checked separately.
        """
        if type(event) is not self._event_class:
            raise EventCodecTypeMismatchError(
                f"Codec for {self._event_class.__name__} cannot encode {type(event).__name__}."
            )
        if event.event_version != self.event_version:
            raise EventCodecVersionMismatchError(
                f"Event version no longer matches codec for {self.event_type}."
            )
        payload = require_json_object(self._codec.encode(event), "payload")
        decoded = self.decode(
            payload, event_id=event.event_id, occurred_at=event.occurred_at, recorded_at=event.recorded_at
        )
        if decoded != event:
            raise EventCodecContractError(f"Codec for {self.event_type} does not preserve event data.")
        return payload


class EventOutboxCodecRegistry:
    """Separate current encoders from versioned readers.

    Register one current codec per event class and optional historical decoders
    per persisted identity. Unknown versions fail closed; there is no fallback
    to the latest version. Registration failures leave both indexes unchanged.
    """

    def __init__(self) -> None:
        """Create an empty codec registry."""
        self._codecs_by_event_class: dict[type[Event], ErasedEventPayloadCodec] = {}
        self._codecs_by_identity: dict[tuple[str, int], ErasedEventPayloadDecoder] = {}

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
            codec: Current payload codec whose version equals the class version.

        Raises:
            DuplicateEventCodecError: If the class or ``(type, version)``
                identity is already registered.
            EventCodecTypeMismatchError: If ``codec.event_class`` differs
                from ``event_class``.
            EventCodecVersionMismatchError: If the codec's version is not current.
            TypeError: If an identity field has an invalid runtime type.
            ValueError: If the name is blank/padded or a version is not positive.
        """
        erased_codec = CodecAdapter(event_class, codec)
        identity = (erased_codec.event_type, erased_codec.event_version)

        if event_class in self._codecs_by_event_class:
            raise DuplicateEventCodecError(f"Codec already registered for {event_class.__name__}.")

        if identity in self._codecs_by_identity:
            event_type, event_version = identity
            raise DuplicateEventCodecError(
                f"Codec already registered for event identity ({event_type!r}, {event_version})."
            )

        self._codecs_by_event_class[event_class] = erased_codec
        self._codecs_by_identity[identity] = erased_codec

    def register_decoder[E: Event](self, event_class: type[E], decoder: EventPayloadDecoder[E]) -> None:
        """Register a historical reader without changing the current encoder.

        Args:
            event_class: Current class reconstructed by the historical reader.
            decoder: Reader for a strictly older persisted payload version.

        Raises:
            DuplicateEventCodecError: If the persisted identity is occupied.
            EventCodecTypeMismatchError: If the advertised class differs.
            EventCodecVersionMismatchError: If the version is current or future.
            TypeError: If an identity field has an invalid runtime type.
            ValueError: If the name is blank/padded or a version is not positive.

        Readers may be registered before or after the current codec. Historical
        transformation rules belong to the decoder, not the registry.
        """
        adapter = DecoderAdapter(event_class, decoder)
        if adapter.event_version >= event_class.event_version:
            raise EventCodecVersionMismatchError(
                f"Historical decoder for {event_class.__name__} must precede "
                f"version {event_class.event_version}."
            )
        identity = (adapter.event_type, adapter.event_version)
        if identity in self._codecs_by_identity:
            raise DuplicateEventCodecError(f"Codec already registered for event identity {identity!r}.")
        self._codecs_by_identity[identity] = adapter

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

    def for_identity(self, event_type: str, event_version: int) -> ErasedEventPayloadDecoder:
        """Resolve a reader for the exact persisted identity, never a fallback.

        Raises:
            EventCodecNotFoundError: If the persisted identity is not
                registered.
            TypeError: If the name or version has an invalid runtime type.
            ValueError: If the name is blank/padded or the version is not positive.
        """
        event_type = _require_event_type(event_type)
        event_version = require_positive_int(event_version, "event_version")
        try:
            return self._codecs_by_identity[(event_type, event_version)]
        except KeyError as exc:
            raise EventCodecNotFoundError(
                f"No codec registered for event identity ({event_type!r}, {event_version})."
            ) from exc


def _require_event_type(value: object) -> str:
    """Require a canonical nonblank wire name without silently changing it."""
    normalized = require_non_empty_str(value, "event_type")
    if normalized != value:
        raise ValueError("event_type must not contain surrounding whitespace.")
    return normalized
