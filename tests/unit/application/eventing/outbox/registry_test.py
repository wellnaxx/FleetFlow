"""Tests for typed outbox codec registration and erased dispatch."""

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.eventing.outbox.errors import (
    DuplicateEventCodecError,
    EventCodecNotFoundError,
    EventCodecTypeMismatchError,
)
from src.application.eventing.outbox.registry import (
    CodecAdapter,
    ErasedEventPayloadCodec,
    EventOutboxCodecRegistry,
)
from src.shared.event import Event
from src.shared.json_types import JSONObject

OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, tzinfo=UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class _SampleEvent(Event):
    value: int


@dataclass(frozen=True, slots=True, kw_only=True)
class _OtherEvent(Event):
    value: int


class _SampleCodec:
    event_class = _SampleEvent

    def __init__(self, *, event_type: str = "SampleEvent", event_version: int = 1) -> None:
        self.event_type = event_type
        self.event_version = event_version

    def encode(self, event: _SampleEvent) -> JSONObject:
        return {"value": event.value}

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> _SampleEvent:
        return _SampleEvent(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            value=cast(int, payload["value"]),
        )


class _OtherCodec:
    event_class = _OtherEvent

    def __init__(self, *, event_type: str = "OtherEvent", event_version: int = 1) -> None:
        self.event_type = event_type
        self.event_version = event_version

    def encode(self, event: _OtherEvent) -> JSONObject:
        return {"value": event.value}

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> _OtherEvent:
        return _OtherEvent(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            value=cast(int, payload["value"]),
        )


class _WrongResultCodec(_SampleCodec):
    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> _SampleEvent:
        return cast(
            _SampleEvent,
            _OtherEvent(
                event_id=event_id,
                occurred_at=occurred_at,
                recorded_at=recorded_at,
                value=cast(int, payload["value"]),
            ),
        )


class EventOutboxCodecRegistryShould(unittest.TestCase):
    def test_registers_one_adapter_under_event_class_and_persisted_identity(self) -> None:
        registry = EventOutboxCodecRegistry()
        codec = _SampleCodec()
        event = _SampleEvent(occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT, value=7)

        registry.register(_SampleEvent, codec)

        by_event = registry.for_event(event)
        by_identity = registry.for_identity("SampleEvent", 1)
        self.assertIs(by_event, by_identity)
        self.assertEqual(by_event.encode(event), {"value": 7})

        event_id = uuid4()
        decoded = by_identity.decode(
            {"value": 8},
            event_id=event_id,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
        )
        self.assertEqual(
            decoded,
            _SampleEvent(
                event_id=event_id,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
                value=8,
            ),
        )

    def test_codec_adapter_explicitly_satisfies_erased_protocol(self) -> None:
        adapter: ErasedEventPayloadCodec = CodecAdapter(_SampleEvent, _SampleCodec())

        self.assertIs(adapter.event_class, _SampleEvent)
        self.assertEqual(adapter.event_type, "SampleEvent")
        self.assertEqual(adapter.event_version, 1)

    def test_rejects_duplicate_event_class(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(_SampleEvent, _SampleCodec())

        with self.assertRaisesRegex(DuplicateEventCodecError, "_SampleEvent"):
            registry.register(_SampleEvent, _SampleCodec(event_type="RenamedSampleEvent"))

    def test_rejects_duplicate_identity_without_partially_registering_class(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(_SampleEvent, _SampleCodec())
        existing = registry.for_identity("SampleEvent", 1)
        other = _OtherEvent(occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT, value=9)

        with self.assertRaisesRegex(DuplicateEventCodecError, "SampleEvent"):
            registry.register(_OtherEvent, _OtherCodec(event_type="SampleEvent"))

        with self.assertRaises(EventCodecNotFoundError):
            registry.for_event(other)
        self.assertIs(registry.for_identity("SampleEvent", 1), existing)

    def test_rejects_non_positive_event_version_before_registration(self) -> None:
        for event_version in (0, -1):
            with self.subTest(event_version=event_version):
                registry = EventOutboxCodecRegistry()

                with self.assertRaisesRegex(ValueError, "codec.event_version must be a positive integer"):
                    registry.register(_SampleEvent, _SampleCodec(event_version=event_version))

                event = _SampleEvent(occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT, value=7)
                with self.assertRaises(EventCodecNotFoundError):
                    registry.for_event(event)

    def test_reports_missing_event_class_and_persisted_identity(self) -> None:
        registry = EventOutboxCodecRegistry()
        event = _SampleEvent(occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT, value=7)

        with self.assertRaisesRegex(EventCodecNotFoundError, "_SampleEvent"):
            registry.for_event(event)

        with self.assertRaisesRegex(EventCodecNotFoundError, "MissingEvent"):
            registry.for_identity("MissingEvent", 3)

    def test_adapter_rejects_mismatched_advertised_event_class(self) -> None:
        mismatched = cast(EventPayloadCodec[_SampleEvent], _OtherCodec())

        with self.assertRaisesRegex(EventCodecTypeMismatchError, "cannot be registered"):
            CodecAdapter(_SampleEvent, mismatched)

    def test_adapter_rejects_wrong_event_on_encode(self) -> None:
        adapter: ErasedEventPayloadCodec = CodecAdapter(_SampleEvent, _SampleCodec())
        event = _OtherEvent(occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT, value=7)

        with self.assertRaisesRegex(EventCodecTypeMismatchError, "cannot encode _OtherEvent"):
            adapter.encode(event)

    def test_adapter_rejects_wrong_event_returned_by_decoder(self) -> None:
        adapter: ErasedEventPayloadCodec = CodecAdapter(_SampleEvent, _WrongResultCodec())

        with self.assertRaisesRegex(EventCodecTypeMismatchError, "decoded _OtherEvent"):
            adapter.decode(
                {"value": 7},
                event_id=uuid4(),
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            )


if __name__ == "__main__":
    unittest.main()
