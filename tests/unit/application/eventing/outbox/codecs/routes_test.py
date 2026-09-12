"""Route-created outbox payload serialization and validation contracts."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

from src.application.eventing.outbox.codecs.routes import RouteCreatedEventPayloadCodec
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.domain.enums.route_status import RouteStatus
from src.domain.events.route_events import RouteCreated
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)
DEPARTURE = datetime(2030, 1, 3, 6, 30, 45, 123456)
COMPLETION = datetime(2030, 1, 4, 18, 45, 30, 654321)


class RouteCreatedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = RouteCreatedEventPayloadCodec()
        self.payload: JSONObject = {
            "route_id": 19,
            "locations": ["SYD", "BNE", "MEL"],
            "departure_time": DEPARTURE.isoformat(),
            "initial_status": RouteStatus.SCHEDULED.value,
            "expected_completion_time": COMPLETION.isoformat(),
        }

    def decode(self, payload: JSONObject) -> RouteCreated:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_all_statuses_and_nullable_timestamps(self) -> None:
        for status in RouteStatus:
            for departure in (None, DEPARTURE):
                for completion in (None, COMPLETION):
                    with self.subTest(status=status, departure=departure, completion=completion):
                        event = RouteCreated(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            route_id=19,
                            locations=(LocationCode("SYD"), LocationCode("BNE"), LocationCode("MEL")),
                            departure_time=departure,
                            initial_status=status,
                            expected_completion_time=completion,
                        )
                        expected = dict(self.payload)
                        expected.update(
                            initial_status=status.value,
                            departure_time=departure.isoformat() if departure is not None else None,
                            expected_completion_time=completion.isoformat() if completion is not None else None,
                        )
                        encoded = self.codec.encode(event)
                        self.assertEqual(encoded, expected)
                        self.assertIs(type(encoded["route_id"]), int)
                        self.assertIs(type(encoded["initial_status"]), str)
                        self.assertIs(type(encoded["locations"]), list)
                        for location in cast(list[JSONValue], encoded["locations"]):
                            self.assertIs(type(location), str)
                        restored = self.decode(
                            cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False)))
                        )
                        self.assertIs(type(restored), RouteCreated)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.initial_status, status)
                        self.assertIs(type(restored.locations), tuple)
                        for location in restored.locations:
                            self.assertIsInstance(location, LocationCode)

    def test_requires_every_key_including_nullable_timestamps(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_and_metadata_keys(self) -> None:
        for field in ("unknown", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_validates_route_id_without_coercion(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, False, 1.0, "19", "", [], {})
        for value in wrong_types:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (1, 2**63):
            with self.subTest(value=value):
                self.assertEqual(self.decode({**self.payload, "route_id": value}).route_id, value)

    def test_requires_locations_to_be_a_list(self) -> None:
        values: tuple[object, ...] = (None, True, 1, 1.5, "SYD", {}, ("SYD", "MEL"), {"SYD", "MEL"})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "locations"):
                self.decode({**self.payload, "locations": cast(JSONValue, value)})

    def test_rejects_non_string_locations_with_correct_index(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for index in range(3):
            for value in values:
                locations: list[JSONValue] = ["SYD", "BNE", "MEL"]
                locations[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaisesRegex(TypeError, rf"locations\[{index}\]: expected str"),
                ):
                    self.decode({**self.payload, "locations": locations})

    def test_rejects_blank_locations(self) -> None:
        for index in range(3):
            for value in ("", " \t\n"):
                locations: list[JSONValue] = ["SYD", "BNE", "MEL"]
                locations[index] = value
                with self.subTest(index=index, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, "locations": locations})

    def test_normalizes_locations_without_sorting_or_deduplicating(self) -> None:
        event = self.decode({**self.payload, "locations": [" syd ", "mel", "SYD"]})
        self.assertEqual(event.locations, (LocationCode("SYD"), LocationCode("MEL"), LocationCode("SYD")))
        self.assertEqual(self.codec.encode(event)["locations"], ["SYD", "MEL", "SYD"])

    def test_does_not_reapply_route_path_or_map_policies(self) -> None:
        cases: tuple[list[JSONValue], ...] = ([], ["SYD"], ["SYD", "SYD"], ["CUSTOM_A", "CUSTOM_B"])
        for locations in cases:
            with self.subTest(locations=locations):
                event = self.decode({**self.payload, "locations": locations})
                self.assertEqual(self.codec.encode(event)["locations"], locations)

    def test_rejects_unknown_status_values_and_wrong_types(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "initial_status"):
                self.decode({**self.payload, "initial_status": value})
        for value in ("unknown", "", "scheduled", " SCHEDULED "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decode({**self.payload, "initial_status": value})

    def test_rejects_non_string_timestamps_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, DEPARTURE)
        for field in ("departure_time", "expected_completion_time"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_timestamps(self) -> None:
        for field in ("departure_time", "expected_completion_time"):
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_timestamp_text_preserves_parse_error_as_cause(self) -> None:
        for field in ("departure_time", "expected_completion_time"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_payload_and_location_list_are_not_mutated_or_retained(self) -> None:
        original = cast(JSONObject, json.loads(json.dumps(self.payload)))
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        cast(list[JSONValue], self.payload["locations"])[0] = "PER"
        self.assertEqual(event.locations[0], LocationCode("SYD"))
        encoded = self.codec.encode(event)
        cast(list[JSONValue], encoded["locations"]).append("PER")
        encoded["route_id"] = 999
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("route_created", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, RouteCreated)
        self.assertEqual(adapter.event_version, RouteCreated.event_version)
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("route_created", version)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
            ("event_id", None, TypeError),
            ("event_id", str(EVENT_ID), TypeError),
            ("occurred_at", None, TypeError),
            ("occurred_at", "2030-01-02", TypeError),
            ("recorded_at", None, TypeError),
            ("recorded_at", "2030-01-02", TypeError),
            ("occurred_at", OCCURRED_AT.replace(tzinfo=UTC), ValueError),
            ("recorded_at", RECORDED_AT.replace(tzinfo=None), ValueError),
            ("recorded_at", RECORDED_AT.astimezone(timezone(timedelta(hours=2))), ValueError),
        )
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                metadata: dict[str, object] = {
                    "event_id": EVENT_ID,
                    "occurred_at": OCCURRED_AT,
                    "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )
