"""Route lifecycle outbox payload serialization and validation contracts."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from itertools import product
from typing import cast
from uuid import UUID

from src.application.eventing.outbox.codecs.routes import (
    PackageAssignedToRouteEventPayloadCodec,
    PackageDetachedFromRouteEventPayloadCodec,
    RouteCreatedEventPayloadCodec,
    RouteScheduledEventPayloadCodec,
    TruckAssignedToRouteEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_status import TruckStatus
from src.domain.events.route_events import (
    PackageAssignedToRoute,
    PackageDetachedFromRoute,
    RouteCreated,
    RouteScheduled,
    TruckAssignedToRoute,
)
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)
DEPARTURE = datetime(2030, 1, 3, 6, 30, 45, 123456)
COMPLETION = datetime(2030, 1, 4, 18, 45, 30, 654321)


class TruckAssignedToRouteCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = TruckAssignedToRouteEventPayloadCodec()
        self.previous_from = DEPARTURE - timedelta(days=1)
        self.previous_until = COMPLETION - timedelta(days=1)
        self.payload: JSONObject = {
            "truck_id": 1001,
            "previous_route_id": 12,
            "new_route_id": 19,
            "previous_status": TruckStatus.FREE.value,
            "new_status": TruckStatus.ON_THE_WAY.value,
            "previous_location": "MEL",
            "new_location": "SYD",
            "previous_busy_from": self.previous_from.isoformat(),
            "new_busy_from": DEPARTURE.isoformat(),
            "previous_busy_until": self.previous_until.isoformat(),
            "new_busy_until": COMPLETION.isoformat(),
        }
        self.timestamp_fields = ("previous_busy_from", "new_busy_from", "previous_busy_until", "new_busy_until")

    def decode(self, payload: JSONObject) -> TruckAssignedToRoute:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_all_nullable_combinations(self) -> None:
        for route_id, previous_from, new_from, previous_until, new_until in product(
            (None, 12), (None, self.previous_from), (None, DEPARTURE),
            (None, self.previous_until), (None, COMPLETION),
        ):
            with self.subTest(
                route=route_id, previous_from=previous_from, new_from=new_from,
                previous_until=previous_until, new_until=new_until,
            ):
                event = TruckAssignedToRoute(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    truck_id=1001,
                    previous_route_id=route_id,
                    new_route_id=19,
                    previous_status=TruckStatus.FREE,
                    new_status=TruckStatus.ON_THE_WAY,
                    previous_location=LocationCode("MEL"),
                    new_location=LocationCode("SYD"),
                    previous_busy_from=previous_from,
                    new_busy_from=new_from,
                    previous_busy_until=previous_until,
                    new_busy_until=new_until,
                )
                expected = dict(self.payload)
                expected["previous_route_id"] = route_id
                for field, value in zip(
                    self.timestamp_fields, (previous_from, new_from, previous_until, new_until), strict=True
                ):
                    expected[field] = value.isoformat() if value is not None else None
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                for field in ("truck_id", "new_route_id"):
                    self.assertIs(type(encoded[field]), int)
                self.assertIs(type(encoded["previous_route_id"]), type(route_id))
                for field in (
                    "previous_status", "new_status", "previous_location", "new_location", *self.timestamp_fields
                ):
                    if encoded[field] is not None:
                        self.assertIs(type(encoded[field]), str)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), TruckAssignedToRoute)
                self.assertEqual(restored, event)
                self.assertIs(restored.previous_status, TruckStatus.FREE)
                self.assertIs(restored.new_status, TruckStatus.ON_THE_WAY)
                self.assertIsInstance(restored.previous_location, LocationCode)
                self.assertIsInstance(restored.new_location, LocationCode)

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
        wrong_types: tuple[JSONValue, ...] = (True, False, 1001.0, "1001", "", [], {})
        for field in ("truck_id", "previous_route_id", "new_route_id"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 2**63):
                with self.subTest(field=field, value=value):
                    self.assertEqual(getattr(self.decode({**self.payload, field: value}), field), value)

    def test_accepts_truck_ids_inside_and_outside_seeded_fleet_range(self) -> None:
        for truck_id in (1, 1000, 1001, 1040, 1041, 2**63):
            with self.subTest(truck_id=truck_id):
                payload = {**self.payload, "truck_id": truck_id}
                event = self.decode(payload)
                self.assertEqual(event.truck_id, truck_id)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_null_truck_and_new_route_ids(self) -> None:
        for field in ("truck_id", "new_route_id"):
            with self.subTest(field=field), self.assertRaisesRegex(TypeError, field):
                self.decode({**self.payload, field: None})

    def test_preserves_all_status_values_without_reapplying_transition_rules(self) -> None:
        for previous_status, new_status in product(TruckStatus, repeat=2):
            with self.subTest(previous_status=previous_status, new_status=new_status):
                payload = {
                    **self.payload, "previous_status": previous_status.value, "new_status": new_status.value
                }
                event = self.decode(payload)
                self.assertIs(event.previous_status, previous_status)
                self.assertIs(event.new_status, new_status)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_invalid_statuses(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_status", "new_status"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", "unknown", "FREE", "ON_THE_WAY", " Free ", "free"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, field: value})

    def test_validates_and_normalizes_both_locations(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_location", "new_location"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", " \t\n"):
                with self.subTest(field=field, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, field: value})
            event = self.decode({**self.payload, field: " bne "})
            self.assertEqual(getattr(event, field), LocationCode("BNE"))

    def test_preserves_unchanged_location_and_busy_window(self) -> None:
        payload = {
            **self.payload,
            "new_location": "MEL",
            "new_busy_from": self.previous_from.isoformat(),
            "new_busy_until": self.previous_until.isoformat(),
        }
        event = self.decode(payload)
        self.assertEqual(event.previous_location, event.new_location)
        self.assertEqual(event.previous_busy_from, event.new_busy_from)
        self.assertEqual(event.previous_busy_until, event.new_busy_until)
        self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_non_string_busy_timestamps_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, COMPLETION)
        for field in self.timestamp_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_busy_timestamps(self) -> None:
        for field in self.timestamp_fields:
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_timestamp_text_preserves_parse_error_as_cause(self) -> None:
        for field in self.timestamp_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["previous_route_id"] = None
        self.assertEqual(event.previous_route_id, 12)
        encoded = self.codec.encode(event)
        encoded["new_busy_until"] = None
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_route_codecs(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        registry.register(RouteScheduled, RouteScheduledEventPayloadCodec())
        registry.register(PackageAssignedToRoute, PackageAssignedToRouteEventPayloadCodec())
        registry.register(PackageDetachedFromRoute, PackageDetachedFromRouteEventPayloadCodec())
        registry.register(TruckAssignedToRoute, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("truck_assigned_to_route", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, TruckAssignedToRoute)
        self.assertEqual(adapter.event_version, TruckAssignedToRoute.event_version)
        for name in (
            "route_created", "route_scheduled", "package_assigned_to_route", "package_detached_from_route"
        ):
            self.assertIsNot(adapter, registry.for_identity(name, 2))
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("truck_assigned_to_route", version)

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


class PackageDetachedFromRouteCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = PackageDetachedFromRouteEventPayloadCodec()
        self.previous_arrival = COMPLETION - timedelta(days=1)
        self.payload: JSONObject = {
            "package_id": 7,
            "previous_route_id": 12,
            "new_route_id": 19,
            "previous_status": ItemStatus.IN_PROGRESS.value,
            "new_status": ItemStatus.TODO.value,
            "previous_location": "MEL",
            "new_location": "SYD",
            "previous_expected_arrival": self.previous_arrival.isoformat(),
            "new_expected_arrival": COMPLETION.isoformat(),
            "reason": PackageDetachmentReason.ROUTE_REMOVED.value,
        }
        self.timestamp_fields = ("previous_expected_arrival", "new_expected_arrival")

    def decode(self, payload: JSONObject) -> PackageDetachedFromRoute:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_every_reason_and_nullable_combination(self) -> None:
        for reason in PackageDetachmentReason:
            for new_route_id in (None, 19):
                for previous_arrival in (None, self.previous_arrival):
                    for new_arrival in (None, COMPLETION):
                        with self.subTest(
                            reason=reason, route=new_route_id, previous=previous_arrival, new=new_arrival
                        ):
                            event = PackageDetachedFromRoute(
                                event_id=EVENT_ID,
                                occurred_at=OCCURRED_AT,
                                recorded_at=RECORDED_AT,
                                package_id=7,
                                previous_route_id=12,
                                new_route_id=new_route_id,
                                previous_status=ItemStatus.IN_PROGRESS,
                                new_status=ItemStatus.TODO,
                                previous_location=LocationCode("MEL"),
                                new_location=LocationCode("SYD"),
                                previous_expected_arrival=previous_arrival,
                                new_expected_arrival=new_arrival,
                                reason=reason,
                            )
                            expected = dict(self.payload)
                            expected.update(
                                new_route_id=new_route_id,
                                previous_expected_arrival=(
                                    previous_arrival.isoformat() if previous_arrival is not None else None
                                ),
                                new_expected_arrival=(
                                    new_arrival.isoformat() if new_arrival is not None else None
                                ),
                                reason=reason.value,
                            )
                            encoded = self.codec.encode(event)
                            self.assertEqual(encoded, expected)
                            for field in ("package_id", "previous_route_id"):
                                self.assertIs(type(encoded[field]), int)
                            self.assertIs(type(encoded["new_route_id"]), type(new_route_id))
                            for field in (
                                "previous_status", "new_status", "previous_location", "new_location", "reason",
                                *self.timestamp_fields,
                            ):
                                if encoded[field] is not None:
                                    self.assertIs(type(encoded[field]), str)
                            restored = self.decode(
                                cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False)))
                            )
                            self.assertIs(type(restored), PackageDetachedFromRoute)
                            self.assertEqual(restored, event)
                            self.assertIs(restored.reason, reason)
                            self.assertIs(restored.previous_status, ItemStatus.IN_PROGRESS)
                            self.assertIs(restored.new_status, ItemStatus.TODO)
                            self.assertIsInstance(restored.previous_location, LocationCode)
                            self.assertIsInstance(restored.new_location, LocationCode)

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
        for field in ("package_id", "previous_route_id", "new_route_id"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 2**63):
                with self.subTest(field=field, value=value):
                    self.assertEqual(getattr(self.decode({**self.payload, field: value}), field), value)

    def test_rejects_null_package_and_previous_route_ids(self) -> None:
        for field in ("package_id", "previous_route_id"):
            with self.subTest(field=field), self.assertRaisesRegex(TypeError, field):
                self.decode({**self.payload, field: None})

    def test_preserves_status_values_without_reapplying_transition_rules(self) -> None:
        for previous_status in ItemStatus:
            for new_status in ItemStatus:
                with self.subTest(previous_status=previous_status, new_status=new_status):
                    payload = {
                        **self.payload,
                        "previous_status": previous_status.value,
                        "new_status": new_status.value,
                    }
                    event = self.decode(payload)
                    self.assertIs(event.previous_status, previous_status)
                    self.assertIs(event.new_status, new_status)
                    self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_invalid_statuses_and_reasons(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_status", "new_status", "reason"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", "unknown", "TODO", " In Progress ", "route_removed", " ROUTE_REMOVED "):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, field: value})

    def test_validates_and_normalizes_both_locations(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_location", "new_location"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", " \t\n"):
                with self.subTest(field=field, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, field: value})
            event = self.decode({**self.payload, field: " bne "})
            self.assertEqual(getattr(event, field), LocationCode("BNE"))

    def test_preserves_unchanged_location_and_arrival(self) -> None:
        payload = {
            **self.payload,
            "new_location": "MEL",
            "new_expected_arrival": self.previous_arrival.isoformat(),
        }
        event = self.decode(payload)
        self.assertEqual(event.previous_location, event.new_location)
        self.assertEqual(event.previous_expected_arrival, event.new_expected_arrival)
        self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_non_string_arrivals_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, COMPLETION)
        for field in self.timestamp_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_arrivals(self) -> None:
        for field in self.timestamp_fields:
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_arrival_text_preserves_parse_error_as_cause(self) -> None:
        for field in self.timestamp_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["new_route_id"] = None
        self.assertEqual(event.new_route_id, 19)
        encoded = self.codec.encode(event)
        encoded["new_expected_arrival"] = None
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_other_route_codecs(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        registry.register(RouteScheduled, RouteScheduledEventPayloadCodec())
        registry.register(PackageAssignedToRoute, PackageAssignedToRouteEventPayloadCodec())
        registry.register(PackageDetachedFromRoute, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("package_detached_from_route", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, PackageDetachedFromRoute)
        self.assertEqual(adapter.event_version, PackageDetachedFromRoute.event_version)
        for name in ("route_created", "route_scheduled", "package_assigned_to_route"):
            self.assertIsNot(adapter, registry.for_identity(name, 2))
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("package_detached_from_route", version)

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


class PackageAssignedToRouteCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = PackageAssignedToRouteEventPayloadCodec()
        self.previous_arrival = COMPLETION - timedelta(days=1)
        self.payload: JSONObject = {
            "package_id": 7,
            "previous_route_id": 12,
            "new_route_id": 19,
            "previous_expected_arrival": self.previous_arrival.isoformat(),
            "new_expected_arrival": COMPLETION.isoformat(),
        }
        self.timestamp_fields = ("previous_expected_arrival", "new_expected_arrival")

    def decode(self, payload: JSONObject) -> PackageAssignedToRoute:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_all_nullable_combinations(self) -> None:
        for previous_route_id in (None, 12):
            for previous_arrival in (None, self.previous_arrival):
                for new_arrival in (None, COMPLETION):
                    with self.subTest(route=previous_route_id, previous=previous_arrival, new=new_arrival):
                        event = PackageAssignedToRoute(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            package_id=7,
                            previous_route_id=previous_route_id,
                            new_route_id=19,
                            previous_expected_arrival=previous_arrival,
                            new_expected_arrival=new_arrival,
                        )
                        expected = dict(self.payload)
                        expected.update(
                            previous_route_id=previous_route_id,
                            previous_expected_arrival=(
                                previous_arrival.isoformat() if previous_arrival is not None else None
                            ),
                            new_expected_arrival=new_arrival.isoformat() if new_arrival is not None else None,
                        )
                        encoded = self.codec.encode(event)
                        self.assertEqual(encoded, expected)
                        for field in ("package_id", "new_route_id"):
                            self.assertIs(type(encoded[field]), int)
                        self.assertIs(type(encoded["previous_route_id"]), type(previous_route_id))
                        for field in self.timestamp_fields:
                            if encoded[field] is not None:
                                self.assertIs(type(encoded[field]), str)
                        restored = self.decode(
                            cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False)))
                        )
                        self.assertIs(type(restored), PackageAssignedToRoute)
                        self.assertEqual(restored, event)

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
        for field in ("package_id", "previous_route_id", "new_route_id"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 2**63):
                with self.subTest(field=field, value=value):
                    self.assertEqual(getattr(self.decode({**self.payload, field: value}), field), value)

    def test_rejects_null_package_and_new_route_ids(self) -> None:
        for field in ("package_id", "new_route_id"):
            with self.subTest(field=field), self.assertRaisesRegex(TypeError, field):
                self.decode({**self.payload, field: None})

    def test_rejects_non_string_arrivals_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, COMPLETION)
        for field in self.timestamp_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_arrivals(self) -> None:
        for field in self.timestamp_fields:
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_arrival_text_preserves_parse_error_as_cause(self) -> None:
        for field in self.timestamp_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_preserves_earlier_and_unchanged_arrival_estimates(self) -> None:
        for arrival in (self.previous_arrival, self.previous_arrival - timedelta(days=2)):
            with self.subTest(arrival=arrival):
                payload = {**self.payload, "new_expected_arrival": arrival.isoformat()}
                event = self.decode(payload)
                self.assertEqual(event.previous_expected_arrival, self.previous_arrival)
                self.assertEqual(event.new_expected_arrival, arrival)
                self.assertEqual(self.codec.encode(event), payload)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["previous_route_id"] = None
        self.assertEqual(event.previous_route_id, 12)
        encoded = self.codec.encode(event)
        encoded["new_expected_arrival"] = None
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_route_codecs(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        registry.register(RouteScheduled, RouteScheduledEventPayloadCodec())
        registry.register(PackageAssignedToRoute, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("package_assigned_to_route", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, PackageAssignedToRoute)
        self.assertEqual(adapter.event_version, PackageAssignedToRoute.event_version)
        for name in ("route_created", "route_scheduled"):
            self.assertIsNot(adapter, registry.for_identity(name, 2))
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("package_assigned_to_route", version)

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


class RouteScheduledCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = RouteScheduledEventPayloadCodec()
        self.previous_departure = DEPARTURE - timedelta(days=1)
        self.previous_completion = COMPLETION - timedelta(days=1)
        self.payload: JSONObject = {
            "route_id": 19,
            "previous_status": RouteStatus.PLANNED.value,
            "new_status": RouteStatus.SCHEDULED.value,
            "previous_departure_time": self.previous_departure.isoformat(),
            "new_departure_time": DEPARTURE.isoformat(),
            "previous_expected_completion_time": self.previous_completion.isoformat(),
            "new_expected_completion_time": COMPLETION.isoformat(),
        }
        self.timestamp_fields = (
            "previous_departure_time", "new_departure_time",
            "previous_expected_completion_time", "new_expected_completion_time",
        )

    def decode(self, payload: JSONObject) -> RouteScheduled:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_nullable_previous_timestamps(self) -> None:
        for previous_departure in (None, self.previous_departure):
            for previous_completion in (None, self.previous_completion):
                with self.subTest(departure=previous_departure, completion=previous_completion):
                    event = RouteScheduled(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        route_id=19,
                        previous_status=RouteStatus.PLANNED,
                        new_status=RouteStatus.SCHEDULED,
                        previous_departure_time=previous_departure,
                        new_departure_time=DEPARTURE,
                        previous_expected_completion_time=previous_completion,
                        new_expected_completion_time=COMPLETION,
                    )
                    expected = dict(self.payload)
                    expected.update(
                        previous_departure_time=(
                            previous_departure.isoformat() if previous_departure is not None else None
                        ),
                        previous_expected_completion_time=(
                            previous_completion.isoformat() if previous_completion is not None else None
                        ),
                    )
                    encoded = self.codec.encode(event)
                    self.assertEqual(encoded, expected)
                    self.assertIs(type(encoded["route_id"]), int)
                    for field in ("previous_status", "new_status", *self.timestamp_fields):
                        if encoded[field] is not None:
                            self.assertIs(type(encoded[field]), str)
                    restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                    self.assertIs(type(restored), RouteScheduled)
                    self.assertEqual(restored, event)
                    self.assertIs(restored.previous_status, RouteStatus.PLANNED)
                    self.assertIs(restored.new_status, RouteStatus.SCHEDULED)

    def test_preserves_all_status_values_without_reapplying_transition_rules(self) -> None:
        for previous_status in RouteStatus:
            for new_status in RouteStatus:
                with self.subTest(previous_status=previous_status, new_status=new_status):
                    payload = {
                        **self.payload,
                        "previous_status": previous_status.value,
                        "new_status": new_status.value,
                    }
                    event = self.decode(payload)
                    self.assertIs(event.previous_status, previous_status)
                    self.assertIs(event.new_status, new_status)
                    self.assertEqual(self.codec.encode(event), payload)

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

    def test_rejects_unknown_statuses_and_wrong_types_for_both_fields(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_status", "new_status"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("unknown", "", "scheduled", " SCHEDULED "):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, field: value})

    def test_rejects_null_new_timestamps(self) -> None:
        for field in ("new_departure_time", "new_expected_completion_time"):
            with self.subTest(field=field), self.assertRaisesRegex(TypeError, field):
                self.decode({**self.payload, field: None})

    def test_rejects_non_string_timestamps_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, DEPARTURE)
        for field in self.timestamp_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_timestamps(self) -> None:
        for field in self.timestamp_fields:
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_timestamp_text_preserves_parse_error_as_cause(self) -> None:
        for field in self.timestamp_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["new_departure_time"] = None
        self.assertEqual(event.new_departure_time, DEPARTURE)
        encoded = self.codec.encode(event)
        encoded["route_id"] = 999
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_created(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        registry.register(RouteScheduled, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("route_scheduled", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, RouteScheduled)
        self.assertEqual(adapter.event_version, RouteScheduled.event_version)
        self.assertIsNot(adapter, registry.for_identity("route_created", 2))
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("route_scheduled", version)

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
