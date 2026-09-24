"""Tests for typed outbox codec registration and erased dispatch."""

import unittest
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import ClassVar, cast
from unittest.mock import patch
from uuid import UUID, uuid4

from src.application.eventing.outbox.codec import EventPayloadCodec, EventPayloadDecoder
from src.application.eventing.outbox.codecs.route_lifecycle import RouteCreatedEventPayloadCodec
from src.application.eventing.outbox.codecs.world_state_runtime import WorldStateAdvancedEventPayloadCodec
from src.application.eventing.outbox.errors import (
    DuplicateEventCodecError,
    EventCodecContractError,
    EventCodecNotFoundError,
    EventCodecTypeMismatchError,
    EventCodecVersionMismatchError,
)
from src.application.eventing.outbox.registry import (
    CodecAdapter,
    ErasedEventPayloadCodec,
    EventOutboxCodecRegistry,
)
from src.application.events.world_state_events import WorldStateAdvanced
from src.domain.enums.route_status import RouteStatus
from src.domain.events.route_events import RouteCreated
from src.domain.value_objects.location_code import LocationCode
from src.shared.event import Event
from src.shared.json_types import JSONObject
from src.shared.validation import require_non_negative_int

OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, tzinfo=UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class _SampleEvent(Event):
    value: int


@dataclass(frozen=True, slots=True, kw_only=True)
class _OtherEvent(Event):
    value: int


@dataclass(frozen=True, slots=True, kw_only=True)
class _VersionedEvent(Event):
    event_version: ClassVar[int] = 3
    value: int


class _HistoricalDecoder:
    event_class = _VersionedEvent
    event_type = "versioned_event"

    def __init__(self, event_version: int = 1) -> None:
        self.event_version = event_version

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> _VersionedEvent:
        return _VersionedEvent(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            value=require_non_negative_int(payload["legacy_value"], "legacy_value"),
        )


class _CurrentCodec:
    event_class = _VersionedEvent
    event_type = "versioned_event"
    event_version = 3

    def encode(self, event: _VersionedEvent) -> JSONObject:
        return {"value": event.value}

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> _VersionedEvent:
        return _VersionedEvent(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            value=require_non_negative_int(payload["value"], "value"),
        )


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

    def test_current_codec_version_must_match_event_class_without_partial_registration(self) -> None:
        for version in (2, 4):
            with self.subTest(version=version):
                registry = EventOutboxCodecRegistry()
                codec = _CurrentCodec()
                codec.event_version = version
                with self.assertRaises(EventCodecVersionMismatchError):
                    registry.register(_VersionedEvent, codec)
                with self.assertRaises(EventCodecNotFoundError):
                    registry.for_identity("versioned_event", version)
                event = _VersionedEvent(occurred_at=OCCURRED_AT, value=1)
                with self.assertRaises(EventCodecNotFoundError):
                    registry.for_event(event)
                registry.register(_VersionedEvent, _CurrentCodec())
                self.assertEqual(registry.for_event(event).event_version, 3)

    def test_rejects_invalid_identity_types_and_names_on_registration_and_lookup(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
            ("event_version", True, TypeError),
            ("event_version", 1.0, TypeError),
            ("event_version", "1", TypeError),
            ("event_version", None, TypeError),
            ("event_version", 0, ValueError),
            ("event_version", -1, ValueError),
            ("event_type", 1, TypeError),
            ("event_type", None, TypeError),
            ("event_type", "", ValueError),
            ("event_type", "   ", ValueError),
            ("event_type", " SampleEvent ", ValueError),
        )
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                registry = EventOutboxCodecRegistry()
                codec = _SampleCodec()
                setattr(codec, field, value)
                with self.assertRaises(error):
                    registry.register(_SampleEvent, codec)
                registry.register(_SampleEvent, _SampleCodec())
                name = cast(str, value) if field == "event_type" else "SampleEvent"
                version = cast(int, value) if field == "event_version" else 1
                with self.assertRaises(error):
                    registry.for_identity(name, version)

    def test_registration_captures_wire_identity(self) -> None:
        registry = EventOutboxCodecRegistry()
        codec = _SampleCodec()
        registry.register(_SampleEvent, codec)
        adapter = registry.for_identity("SampleEvent", 1)

        codec.event_type = "changed"
        codec.event_version = 8

        self.assertEqual((adapter.event_type, adapter.event_version), ("SampleEvent", 1))
        self.assertIs(registry.for_identity("SampleEvent", 1), adapter)
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("changed", 8)

    def test_registration_rejects_invalid_event_class_versions(self) -> None:
        for version, error in ((0, ValueError), (-1, ValueError), (True, TypeError)):
            with (
                self.subTest(version=version),
                patch.object(_VersionedEvent, "event_version", version),
                self.assertRaises(error),
            ):
                EventOutboxCodecRegistry().register(_VersionedEvent, _CurrentCodec())

    def test_encoding_rejects_event_class_version_drift(self) -> None:
        adapter = CodecAdapter(_VersionedEvent, _CurrentCodec())
        event = _VersionedEvent(occurred_at=OCCURRED_AT, value=7)
        with (
            patch.object(_VersionedEvent, "event_version", 4),
            self.assertRaises(EventCodecVersionMismatchError),
        ):
            adapter.encode(event)

    def test_historical_decoders_coexist_with_current_codec_in_either_registration_order(self) -> None:
        for historical_first in (True, False):
            with self.subTest(historical_first=historical_first):
                registry = EventOutboxCodecRegistry()
                if not historical_first:
                    registry.register(_VersionedEvent, _CurrentCodec())
                registry.register_decoder(_VersionedEvent, _HistoricalDecoder(1))
                registry.register_decoder(_VersionedEvent, _HistoricalDecoder(2))
                if historical_first:
                    registry.register(_VersionedEvent, _CurrentCodec())
                event = _VersionedEvent(occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT, value=7)
                current = registry.for_event(event)
                self.assertIs(current, registry.for_identity("versioned_event", 3))
                self.assertEqual(current.encode(event), {"value": 7})
                for version in (1, 2):
                    historical = registry.for_identity("versioned_event", version)
                    self.assertEqual(historical.event_version, version)
                    self.assertFalse(hasattr(historical, "encode"))
                    decoded = historical.decode(
                        {"legacy_value": 7},
                        event_id=event.event_id,
                        occurred_at=event.occurred_at,
                        recorded_at=event.recorded_at,
                    )
                    self.assertEqual(decoded, event)
                    self.assertEqual(decoded.event_version, 3)
                    with self.assertRaises(ValueError):
                        historical.decode(
                            {"legacy_value": -1},
                            event_id=event.event_id,
                            occurred_at=event.occurred_at,
                            recorded_at=event.recorded_at,
                        )

    def test_historical_registration_does_not_enable_encoding_or_unknown_versions(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register_decoder(_VersionedEvent, _HistoricalDecoder())
        event = _VersionedEvent(occurred_at=OCCURRED_AT, value=7)
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_event(event)
        for version in (2, 3, 4):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("versioned_event", version)

    def test_historical_registration_rejects_current_future_or_invalid_versions(self) -> None:
        cases = (
            (0, ValueError),
            (-1, ValueError),
            (True, TypeError),
            (3, EventCodecVersionMismatchError),
            (4, EventCodecVersionMismatchError),
        )
        for version, error in cases:
            with self.subTest(version=version):
                registry = EventOutboxCodecRegistry()
                registry.register(_VersionedEvent, _CurrentCodec())
                current = registry.for_identity("versioned_event", 3)
                with self.assertRaises(error):
                    registry.register_decoder(_VersionedEvent, _HistoricalDecoder(version))
                self.assertIs(registry.for_identity("versioned_event", 3), current)
                registry.register_decoder(_VersionedEvent, _HistoricalDecoder(1))

    def test_duplicate_historical_registration_preserves_both_indexes(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(_VersionedEvent, _CurrentCodec())
        registry.register_decoder(_VersionedEvent, _HistoricalDecoder())
        current = registry.for_identity("versioned_event", 3)
        previous = registry.for_identity("versioned_event", 1)
        with self.assertRaises(DuplicateEventCodecError):
            registry.register_decoder(_VersionedEvent, _HistoricalDecoder())
        self.assertIs(registry.for_identity("versioned_event", 1), previous)
        self.assertIs(registry.for_identity("versioned_event", 3), current)
        event = _VersionedEvent(occurred_at=OCCURRED_AT, value=7)
        self.assertIs(registry.for_event(event), current)

    def test_historical_registration_rejects_mismatched_event_class(self) -> None:
        registry = EventOutboxCodecRegistry()
        decoder = cast(EventPayloadDecoder[_SampleEvent], _HistoricalDecoder())
        with self.assertRaises(EventCodecTypeMismatchError):
            registry.register_decoder(_SampleEvent, decoder)
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("versioned_event", 1)

    def test_current_registration_cannot_overwrite_an_occupied_historical_identity(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register_decoder(_VersionedEvent, _HistoricalDecoder())
        previous = registry.for_identity("versioned_event", 1)
        with self.assertRaises(DuplicateEventCodecError):
            registry.register(_SampleEvent, _SampleCodec(event_type="versioned_event"))
        self.assertIs(registry.for_identity("versioned_event", 1), previous)
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_event(_SampleEvent(occurred_at=OCCURRED_AT, value=7))

    def test_adapter_rejects_lossy_encoding(self) -> None:
        codec = _SampleCodec()
        adapter = CodecAdapter(_SampleEvent, codec)
        event = _SampleEvent(occurred_at=OCCURRED_AT, value=7)
        with (
            patch.object(codec, "encode", return_value={"value": 8}),
            self.assertRaisesRegex(EventCodecContractError, "preserve event data"),
        ):
            adapter.encode(event)

    def test_adapter_rejects_changed_metadata_on_decode(self) -> None:
        codec = _SampleCodec()
        adapter = CodecAdapter(_SampleEvent, codec)
        event = _SampleEvent(occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT, value=7)
        altered = (
            replace(event, event_id=uuid4()),
            replace(event, occurred_at=datetime(2031, 1, 1)),
            replace(event, recorded_at=datetime(2031, 1, 1, tzinfo=UTC)),
        )
        for decoded in altered:
            with (
                self.subTest(decoded=decoded),
                patch.object(codec, "decode", return_value=decoded),
                self.assertRaisesRegex(EventCodecContractError, "metadata"),
            ):
                adapter.decode(
                    {"value": 7}, event_id=event.event_id, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
                )

    def test_adapter_rejects_invalid_json_before_decoding_on_both_paths(self) -> None:
        invalid_payloads: tuple[object, ...] = (
            [],
            {1: "value"},
            {"value": (7,)},
            {"value": float("nan")},
            {"value": float("inf")},
            {"value": OCCURRED_AT},
            {"value": uuid4()},
        )
        codec = _SampleCodec()
        adapter = CodecAdapter(_SampleEvent, codec)
        event = _SampleEvent(occurred_at=OCCURRED_AT, value=7)
        for payload in invalid_payloads:
            with self.subTest(payload=payload), patch.object(codec, "decode") as decode:
                with self.assertRaises(TypeError):
                    adapter.decode(
                        cast(JSONObject, payload),
                        event_id=event.event_id,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                    )
                with patch.object(codec, "encode", return_value=payload), self.assertRaises(TypeError):
                    adapter.encode(event)
                decode.assert_not_called()

    def test_adapter_validates_metadata_before_calling_decoder(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
            ("event_id", "not-a-uuid", TypeError),
            ("occurred_at", RECORDED_AT, ValueError),
            ("recorded_at", OCCURRED_AT, ValueError),
        )
        codec = _SampleCodec()
        adapter = CodecAdapter(_SampleEvent, codec)
        for field, value, error in cases:
            with self.subTest(field=field), patch.object(codec, "decode") as decode:
                with self.assertRaises(error):
                    adapter.decode(
                        {"value": 7},
                        event_id=cast(UUID, value) if field == "event_id" else uuid4(),
                        occurred_at=cast(datetime, value) if field == "occurred_at" else OCCURRED_AT,
                        recorded_at=cast(datetime, value) if field == "recorded_at" else RECORDED_AT,
                    )
                decode.assert_not_called()

    def test_decoder_cannot_mutate_caller_or_outbound_payload(self) -> None:
        codec = _SampleCodec()
        adapter = CodecAdapter(_SampleEvent, codec)
        event = _SampleEvent(occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT, value=7)
        payload: JSONObject = {"value": 7, "nested": [1, {"key": "original"}]}

        def mutate(payload: JSONObject, **_metadata: object) -> _SampleEvent:
            nested = cast(list[object], payload["nested"])
            cast(dict[str, object], nested[1])["key"] = "changed"
            payload.clear()
            return event

        with patch.object(codec, "decode", side_effect=mutate):
            decoded = adapter.decode(
                payload, event_id=event.event_id, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            )
            self.assertEqual(decoded, event)
            with patch.object(codec, "encode", return_value=payload):
                self.assertEqual(adapter.encode(event), {"value": 7, "nested": [1, {"key": "original"}]})
        self.assertEqual(payload, {"value": 7, "nested": [1, {"key": "original"}]})

    def test_outbound_payload_uses_concrete_decoder_counter_validation(self) -> None:
        registry = EventOutboxCodecRegistry()
        codec = WorldStateAdvancedEventPayloadCodec()
        registry.register(WorldStateAdvanced, codec)
        event = WorldStateAdvanced(
            occurred_at=OCCURRED_AT,
            routes_updated=-1,
            packages_updated=0,
            trucks_moved=0,
            trucks_released=0,
            trucks_reconciled=0,
        )
        self.assertEqual(codec.encode(event)["routes_updated"], -1)
        with self.assertRaisesRegex(ValueError, "routes_updated"):
            registry.for_event(event).encode(event)
        valid = replace(event, routes_updated=0)
        self.assertEqual(registry.for_event(valid).encode(valid), codec.encode(valid))

    def test_outbound_payload_uses_concrete_decoder_business_time_validation(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        event = RouteCreated(
            occurred_at=OCCURRED_AT,
            route_id=7,
            locations=(LocationCode("SYD"), LocationCode("MEL")),
            departure_time=RECORDED_AT,
            initial_status=RouteStatus.SCHEDULED,
            expected_completion_time=None,
        )
        with self.assertRaises(ValueError):
            registry.for_event(event).encode(event)

    def test_encoding_propagates_decoder_validation_failure_unchanged(self) -> None:
        codec = _SampleCodec()
        adapter = CodecAdapter(_SampleEvent, codec)
        failure = ValueError("invalid field")
        with patch.object(codec, "decode", side_effect=failure), self.assertRaises(ValueError) as raised:
            adapter.encode(_SampleEvent(occurred_at=OCCURRED_AT, value=7))
        self.assertIs(raised.exception, failure)


if __name__ == "__main__":
    unittest.main()
