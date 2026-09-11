"""Package lifecycle outbox payload serialization and validation contracts."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

from src.application.eventing.outbox.codecs.packages import (
    PackageCreatedEventPayloadCodec,
    PackageRemovedEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.domain.enums.item_status import ItemStatus
from src.domain.events.package_events import PackageCreated, PackageRemoved
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)
ARRIVAL = datetime(2030, 1, 3, 12, 30, 45, 123456)


class PackageRemovedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = PackageRemovedEventPayloadCodec()
        self.payload: JSONObject = {
            "package_id": 7,
            "customer_id": 12,
            "previous_route_id": 19,
            "previous_status": ItemStatus.IN_PROGRESS.value,
            "previous_location": "BNE",
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": 2.5,
            "previous_expected_arrival": ARRIVAL.isoformat(),
        }

    def decode(self, payload: JSONObject) -> PackageRemoved:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_all_statuses_and_nullable_combinations(self) -> None:
        for status in ItemStatus:
            for route_id in (None, 19):
                for arrival in (None, ARRIVAL):
                    with self.subTest(status=status, route_id=route_id, arrival=arrival):
                        event = PackageRemoved(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            package_id=7,
                            customer_id=12,
                            previous_route_id=route_id,
                            previous_status=status,
                            previous_location=LocationCode("BNE"),
                            start_location=LocationCode("SYD"),
                            end_location=LocationCode("MEL"),
                            weight=2.5,
                            previous_expected_arrival=arrival,
                        )
                        expected = dict(self.payload)
                        expected.update(
                            previous_status=status.value,
                            previous_route_id=route_id,
                            previous_expected_arrival=arrival.isoformat() if arrival is not None else None,
                        )
                        encoded = self.codec.encode(event)
                        self.assertEqual(encoded, expected)
                        for field in ("start_location", "end_location", "previous_location", "previous_status"):
                            self.assertIs(type(encoded[field]), str)
                        for field in ("package_id", "customer_id"):
                            self.assertIs(type(encoded[field]), int)
                        self.assertIs(type(encoded["previous_route_id"]), type(route_id))
                        restored = self.decode(
                            cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False)))
                        )
                        self.assertIs(type(restored), PackageRemoved)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.previous_status, status)
                        self.assertIsInstance(restored.start_location, LocationCode)
                        self.assertIsInstance(restored.end_location, LocationCode)
                        self.assertIsInstance(restored.previous_location, LocationCode)

    def test_requires_every_key_including_nullable_fields(self) -> None:
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

    def test_validates_required_and_optional_ids_without_coercion(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (True, False, 1.0, "7", "", [], {})
        for field in ("package_id", "customer_id", "previous_route_id"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 2**63):
                with self.subTest(field=field, value=value):
                    self.assertEqual(getattr(self.decode({**self.payload, field: value}), field), value)
        for field in ("package_id", "customer_id"):
            with self.subTest(field=field), self.assertRaisesRegex(TypeError, field):
                self.decode({**self.payload, field: None})

    def test_validates_and_normalizes_all_locations(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("start_location", "end_location", "previous_location"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", " \t\n"):
                with self.subTest(field=field, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, field: value})
            event = self.decode({**self.payload, field: " mel "})
            self.assertEqual(getattr(event, field), LocationCode("MEL"))

    def test_rejects_wrong_weight_types(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, "2.5", [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "weight"):
                self.decode({**self.payload, "weight": value})

    def test_rejects_non_positive_non_finite_and_overflowing_weights(self) -> None:
        for value in (0, -1, -0.0, float("nan"), float("inf"), -float("inf"), 10**400):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "weight"):
                self.decode({**self.payload, "weight": value})

    def test_accepts_positive_finite_weights_and_normalizes_to_float(self) -> None:
        for value in (1, 2.5, 5e-324, 1e308):
            with self.subTest(value=value):
                event = self.decode({**self.payload, "weight": value})
                self.assertEqual(event.weight, value)
                self.assertIs(type(event.weight), float)

    def test_rejects_status_names_unknown_values_and_wrong_types(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "previous_status"):
                self.decode({**self.payload, "previous_status": value})
        for value in ("TODO", "IN_PROGRESS", "DONE", "unknown", "", " In Progress "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decode({**self.payload, "previous_status": value})

    def test_rejects_arrival_non_string_values_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, ARRIVAL)
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "previous_expected_arrival"):
                self.decode({**self.payload, "previous_expected_arrival": cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_arrivals(self) -> None:
        for value in (
            "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
            "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
            "2030-01-01T12:00:00-03:00",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "previous_expected_arrival"):
                self.decode({**self.payload, "previous_expected_arrival": value})

    def test_invalid_arrival_text_preserves_parse_error_as_cause(self) -> None:
        with self.assertRaisesRegex(ValueError, "previous_expected_arrival") as raised:
            self.decode({**self.payload, "previous_expected_arrival": "invalid"})
        self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["previous_route_id"] = None
        self.assertEqual(event.previous_route_id, 19)
        encoded = self.codec.encode(event)
        encoded["previous_location"] = "SYD"
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_created(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(PackageCreated, PackageCreatedEventPayloadCodec())
        registry.register(PackageRemoved, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("package_removed", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, PackageRemoved)
        self.assertEqual(adapter.event_version, PackageRemoved.event_version)
        self.assertIsNot(adapter, registry.for_identity("package_created", 2))
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("package_removed", version)

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


class PackageCreatedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = PackageCreatedEventPayloadCodec()
        self.payload: JSONObject = {
            "package_id": 7,
            "customer_id": 12,
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": 2.5,
            "initial_status": ItemStatus.TODO.value,
            "initial_location": "SYD",
            "expected_arrival": ARRIVAL.isoformat(),
        }

    def decode(self, payload: JSONObject) -> PackageCreated:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_and_json_round_trip(self) -> None:
        for status in ItemStatus:
            for arrival in (None, ARRIVAL):
                with self.subTest(status=status, arrival=arrival):
                    event = PackageCreated(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        package_id=7,
                        customer_id=12,
                        start_location=LocationCode("SYD"),
                        end_location=LocationCode("MEL"),
                        weight=2.5,
                        initial_status=status,
                        initial_location=LocationCode("BNE"),
                        expected_arrival=arrival,
                    )
                    expected = dict(self.payload)
                    expected.update(
                        initial_status=status.value,
                        initial_location="BNE",
                        expected_arrival=arrival.isoformat() if arrival is not None else None,
                    )
                    encoded = self.codec.encode(event)
                    self.assertEqual(encoded, expected)
                    for field in ("start_location", "end_location", "initial_location", "initial_status"):
                        self.assertIs(type(encoded[field]), str)
                    restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                    self.assertIs(type(restored), PackageCreated)
                    self.assertEqual(restored, event)
                    self.assertIs(restored.initial_status, status)
                    self.assertIsInstance(restored.start_location, LocationCode)
                    self.assertIsInstance(restored.end_location, LocationCode)
                    self.assertIsInstance(restored.initial_location, LocationCode)

    def test_requires_every_key_including_nullable_arrival(self) -> None:
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
            with self.subTest(field=field):
                payload = dict(self.payload)
                payload[field] = "unexpected"
                with self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                    self.decode(payload)

    def test_validates_each_id_without_coercion(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, False, 1.0, "7", [], {})
        for field in ("package_id", "customer_id"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 2**63):
                with self.subTest(field=field, value=value):
                    event = self.decode({**self.payload, field: value})
                    self.assertEqual(getattr(event, field), value)

    def test_validates_and_normalizes_all_locations(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("start_location", "end_location", "initial_location"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", " \t\n"):
                with self.subTest(field=field, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, field: value})
            event = self.decode({**self.payload, field: " mel "})
            self.assertEqual(getattr(event, field), LocationCode("MEL"))

    def test_rejects_wrong_weight_types(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, "2.5", [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "weight"):
                self.decode({**self.payload, "weight": value})

    def test_rejects_non_positive_non_finite_and_overflowing_weights(self) -> None:
        for value in (0, -1, -0.0, float("nan"), float("inf"), -float("inf"), 10**400):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "weight"):
                self.decode({**self.payload, "weight": value})

    def test_accepts_positive_finite_numeric_weights_and_normalizes_to_float(self) -> None:
        for value in (1, 2.5, 5e-324, 1e308):
            with self.subTest(value=value):
                event = self.decode({**self.payload, "weight": value})
                self.assertEqual(event.weight, value)
                self.assertIs(type(event.weight), float)

    def test_rejects_status_names_unknown_values_and_wrong_types(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "initial_status"):
                self.decode({**self.payload, "initial_status": value})
        for value in ("TODO", "unknown", "", " To Do "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decode({**self.payload, "initial_status": value})

    def test_rejects_arrival_non_string_values_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, ARRIVAL)
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "expected_arrival"):
                self.decode({**self.payload, "expected_arrival": cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_arrivals(self) -> None:
        for value in (
            "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
            "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "expected_arrival"):
                self.decode({**self.payload, "expected_arrival": value})

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["end_location"] = "BNE"
        self.assertEqual(event.end_location, LocationCode("MEL"))
        encoded = self.codec.encode(event)
        encoded["package_id"] = 999
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(PackageCreated, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("package_created", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, PackageCreated)
        self.assertEqual(adapter.event_version, PackageCreated.event_version)
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("package_created", version)

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
