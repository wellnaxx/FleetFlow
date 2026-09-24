"""Route truck assignment and release outbox payload contract tests."""

import unittest
from datetime import datetime, timedelta
from itertools import product
from typing import cast

from src.application.eventing.outbox.codecs.route_lifecycle import (
    RouteCreatedEventPayloadCodec,
    RouteScheduledEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.route_packages import (
    PackageAssignedToRouteEventPayloadCodec,
    PackageDetachedFromRouteEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.route_trucks import (
    TruckAssignedToRouteEventPayloadCodec,
    TruckReleasedFromRouteEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.enums.truck_status import TruckStatus
from src.domain.events.route_events import (
    PackageAssignedToRoute,
    PackageDetachedFromRoute,
    RouteCreated,
    RouteScheduled,
    TruckAssignedToRoute,
    TruckReleasedFromRoute,
)
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_types import JSONObject, JSONValue
from tests.unit.application.eventing.outbox.codecs.helpers import (
    EVENT_ID,
    OCCURRED_AT,
    RECORDED_AT,
    assert_invalid_metadata,
    assert_required_keys,
    decode_payload,
    json_round_trip,
)

DEPARTURE = datetime(2030, 1, 3, 6, 30, 45, 123456)


COMPLETION = datetime(2030, 1, 4, 18, 45, 30, 654321)


class TruckReleasedFromRouteCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = TruckReleasedFromRouteEventPayloadCodec()
        self.previous_from = DEPARTURE - timedelta(days=1)
        self.previous_until = COMPLETION - timedelta(days=1)
        self.payload: JSONObject = {
            "truck_id": 1001,
            "previous_route_id": 12,
            "new_route_id": 19,
            "previous_status": TruckStatus.ON_THE_WAY.value,
            "new_status": TruckStatus.FREE.value,
            "previous_location": "MEL",
            "new_location": "SYD",
            "previous_busy_from": self.previous_from.isoformat(),
            "new_busy_from": DEPARTURE.isoformat(),
            "previous_busy_until": self.previous_until.isoformat(),
            "new_busy_until": COMPLETION.isoformat(),
            "reason": TruckReleaseReason.ROUTE_COMPLETED.value,
        }
        self.timestamp_fields = ("previous_busy_from", "new_busy_from", "previous_busy_until", "new_busy_until")

    def decode(self, payload: JSONObject) -> TruckReleasedFromRoute:
        return decode_payload(self.codec, payload)

    def test_exact_wire_contract_round_trips_every_reason_and_nullable_combination(self) -> None:
        for reason, route_id, previous_from, new_from, previous_until, new_until in product(
            TruckReleaseReason, (None, 19), (None, self.previous_from), (None, DEPARTURE),
            (None, self.previous_until), (None, COMPLETION),
        ):
            with self.subTest(
                reason=reason, route=route_id, previous_from=previous_from, new_from=new_from,
                previous_until=previous_until, new_until=new_until,
            ):
                event = TruckReleasedFromRoute(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    truck_id=1001,
                    previous_route_id=12,
                    new_route_id=route_id,
                    previous_status=TruckStatus.ON_THE_WAY,
                    new_status=TruckStatus.FREE,
                    previous_location=LocationCode("MEL"),
                    new_location=LocationCode("SYD"),
                    previous_busy_from=previous_from,
                    new_busy_from=new_from,
                    previous_busy_until=previous_until,
                    new_busy_until=new_until,
                    reason=reason,
                )
                expected = dict(self.payload)
                expected.update(new_route_id=route_id, reason=reason.value)
                for field, value in zip(
                    self.timestamp_fields, (previous_from, new_from, previous_until, new_until), strict=True
                ):
                    expected[field] = value.isoformat() if value is not None else None
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                for field in ("truck_id", "previous_route_id"):
                    self.assertIs(type(encoded[field]), int)
                self.assertIs(type(encoded["new_route_id"]), type(route_id))
                for field in (
                    "previous_status", "new_status", "previous_location", "new_location", "reason",
                    *self.timestamp_fields,
                ):
                    if encoded[field] is not None:
                        self.assertIs(type(encoded[field]), str)
                restored = self.decode(json_round_trip(encoded))
                self.assertIs(type(restored), TruckReleasedFromRoute)
                self.assertEqual(restored, event)
                self.assertIs(restored.reason, reason)
                self.assertIs(restored.previous_status, TruckStatus.ON_THE_WAY)
                self.assertIs(restored.new_status, TruckStatus.FREE)
                self.assertIsInstance(restored.previous_location, LocationCode)
                self.assertIsInstance(restored.new_location, LocationCode)

    def test_requires_every_key_including_nullable_fields(self) -> None:
        assert_required_keys(self, self.decode, dict(self.payload))

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

    def test_rejects_null_truck_and_previous_route_ids(self) -> None:
        for field in ("truck_id", "previous_route_id"):
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

    def test_rejects_invalid_release_reasons(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for value in wrong_types:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "reason"):
                self.decode({**self.payload, "reason": value})
        for value in ("", "unknown", "route_completed", " ROUTE_REMOVED ", "PACKAGE_REMOVED"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decode({**self.payload, "reason": value})

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
        self.payload["new_route_id"] = None
        self.assertEqual(event.new_route_id, 19)
        encoded = self.codec.encode(event)
        encoded["new_busy_until"] = None
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_assignment(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(TruckAssignedToRoute, TruckAssignedToRouteEventPayloadCodec())
        registry.register(TruckReleasedFromRoute, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("truck_released_from_route", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, TruckReleasedFromRoute)
        self.assertEqual(adapter.event_version, TruckReleasedFromRoute.event_version)
        self.assertIsNot(adapter, registry.for_identity("truck_assigned_to_route", 2))
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("truck_released_from_route", version)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.payload)


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
        return decode_payload(self.codec, payload)

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
                restored = self.decode(json_round_trip(encoded))
                self.assertIs(type(restored), TruckAssignedToRoute)
                self.assertEqual(restored, event)
                self.assertIs(restored.previous_status, TruckStatus.FREE)
                self.assertIs(restored.new_status, TruckStatus.ON_THE_WAY)
                self.assertIsInstance(restored.previous_location, LocationCode)
                self.assertIsInstance(restored.new_location, LocationCode)

    def test_requires_every_key_including_nullable_fields(self) -> None:
        assert_required_keys(self, self.decode, dict(self.payload))

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
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("truck_assigned_to_route", version)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.payload)
