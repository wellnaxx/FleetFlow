"""Reconciliation outbox payload serialization and validation contracts."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from itertools import product
from typing import cast
from uuid import UUID

from src.application.enums.package_reconciliation_reasons import PackageReconciliationReason
from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
from src.application.eventing.outbox.codecs.reconciliation import (
    PackageStateReconciledEventPayloadCodec,
    RouteStateReconciledEventPayloadCodec,
    TruckPositionReconciledEventPayloadCodec,
    TruckRouteReferenceReconciledEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.reconciliation_events import (
    PackageStateReconciled,
    RouteStateReconciled,
    TruckPositionReconciled,
    TruckRouteReferenceReconciled,
)
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.route_schedule import RoutePositionKind
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)
DEPARTURE = datetime(2030, 1, 3, 6, 30, 45, 123456)
COMPLETION = datetime(2030, 1, 4, 18, 45, 30, 654321)


class TruckRouteReferenceReconciledCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = TruckRouteReferenceReconciledEventPayloadCodec()
        self.payload: JSONObject = {"truck_id": 1001, "previous_route_id": 12, "new_route_id": 19}

    def decode(self, payload: JSONObject) -> TruckRouteReferenceReconciled:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_null_and_populated_previous_references(self) -> None:
        for previous_route_id in (None, 12):
            with self.subTest(previous_route_id=previous_route_id):
                event = TruckRouteReferenceReconciled(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    truck_id=1001,
                    previous_route_id=previous_route_id,
                    new_route_id=19,
                )
                expected = {**self.payload, "previous_route_id": previous_route_id}
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                self.assertIs(type(encoded["truck_id"]), int)
                self.assertIs(type(encoded["new_route_id"]), int)
                self.assertIs(type(encoded["previous_route_id"]), type(previous_route_id))
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), TruckRouteReferenceReconciled)
                self.assertEqual(restored, event)

    def test_requires_every_key_including_nullable_previous_reference(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "route_id", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_rejects_wrong_id_types_without_coercion(self) -> None:
        values: tuple[JSONValue, ...] = (True, False, 1.0, "19", "", [], {})
        for field in self.payload:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})

    def test_rejects_null_truck_and_new_route_ids(self) -> None:
        for field in ("truck_id", "new_route_id"):
            with self.subTest(field=field), self.assertRaisesRegex(TypeError, field):
                self.decode({**self.payload, field: None})

    def test_rejects_non_positive_ids_and_accepts_positive_boundaries(self) -> None:
        for field in self.payload:
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 2**63):
                with self.subTest(field=field, value=value):
                    event = self.decode({**self.payload, field: value})
                    self.assertEqual(getattr(event, field), value)
                    self.assertIs(type(self.codec.encode(event)[field]), int)

    def test_accepts_truck_ids_inside_and_outside_seeded_fleet_range(self) -> None:
        for truck_id in (1, 1000, 1001, 1040, 1041, 2**63):
            with self.subTest(truck_id=truck_id):
                payload = {**self.payload, "truck_id": truck_id}
                self.assertEqual(self.codec.encode(self.decode(payload)), payload)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["previous_route_id"] = None
        self.assertEqual(event.previous_route_id, 12)
        encoded = self.codec.encode(event)
        encoded["new_route_id"] = 999
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_one_without_conflicting_with_other_reconciliation_events(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteStateReconciled, RouteStateReconciledEventPayloadCodec())
        registry.register(PackageStateReconciled, PackageStateReconciledEventPayloadCodec())
        registry.register(TruckPositionReconciled, TruckPositionReconciledEventPayloadCodec())
        registry.register(TruckRouteReferenceReconciled, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("truck_route_reference_reconciled", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, TruckRouteReferenceReconciled)
        self.assertEqual(adapter.event_version, TruckRouteReferenceReconciled.event_version)
        for name in ("route_state_reconciled", "package_state_reconciled", "truck_position_reconciled"):
            self.assertIsNot(adapter, registry.for_identity(name, 1))
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("truck_route_reference_reconciled", version)

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
                    "event_id": EVENT_ID, "occurred_at": OCCURRED_AT, "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )


class TruckPositionReconciledCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = TruckPositionReconciledEventPayloadCodec()
        self.payload: JSONObject = {
            "truck_id": 1001,
            "route_id": 19,
            "previous_location": "SYD",
            "new_location": "MEL",
            "previous_in_transit_to": "BNE",
            "new_in_transit_to": "PER",
            "position_kind": RoutePositionKind.IN_TRANSIT.value,
        }
        self.location_fields = (
            "previous_location", "new_location", "previous_in_transit_to", "new_in_transit_to"
        )

    def decode(self, payload: JSONObject) -> TruckPositionReconciled:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_all_position_kinds_and_nullable_combinations(self) -> None:
        for kind, route_id, previous, new, previous_target, new_target in product(
            RoutePositionKind, (None, 19), (None, LocationCode("SYD")), (None, LocationCode("MEL")),
            (None, LocationCode("BNE")), (None, LocationCode("PER")),
        ):
            with self.subTest(
                kind=kind, route=route_id, previous=previous, new=new,
                previous_target=previous_target, new_target=new_target,
            ):
                event = TruckPositionReconciled(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    truck_id=1001,
                    route_id=route_id,
                    previous_location=previous,
                    new_location=new,
                    previous_in_transit_to=previous_target,
                    new_in_transit_to=new_target,
                    position_kind=kind,
                )
                expected = dict(self.payload)
                expected.update(route_id=route_id, position_kind=kind.value)
                for field, value in zip(
                    self.location_fields, (previous, new, previous_target, new_target), strict=True
                ):
                    expected[field] = str(value) if value is not None else None
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                self.assertIs(type(encoded["truck_id"]), int)
                self.assertIs(type(encoded["route_id"]), type(route_id))
                self.assertIs(type(encoded["position_kind"]), str)
                for field in self.location_fields:
                    if expected[field] is None:
                        self.assertIsNone(encoded[field])
                    else:
                        self.assertIs(type(encoded[field]), str)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), TruckPositionReconciled)
                self.assertEqual(restored, event)
                self.assertIs(restored.position_kind, kind)
                for field in self.location_fields:
                    value = getattr(restored, field)
                    if value is not None:
                        self.assertIsInstance(value, LocationCode)

    def test_requires_every_key_including_new_location_and_nullable_fields(self) -> None:
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
        values: tuple[JSONValue, ...] = (True, False, 1.0, "19", "", [], {})
        for field in ("truck_id", "route_id"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 2**63):
                with self.subTest(field=field, value=value):
                    self.assertEqual(getattr(self.decode({**self.payload, field: value}), field), value)
        with self.assertRaisesRegex(TypeError, "truck_id"):
            self.decode({**self.payload, "truck_id": None})

    def test_accepts_truck_ids_inside_and_outside_seeded_fleet_range(self) -> None:
        for truck_id in (1, 1000, 1001, 1040, 1041, 2**63):
            with self.subTest(truck_id=truck_id):
                payload = {**self.payload, "truck_id": truck_id}
                self.assertEqual(self.codec.encode(self.decode(payload)), payload)

    def test_validates_and_normalizes_all_four_locations(self) -> None:
        values: tuple[JSONValue, ...] = (True, False, 1, 1.5, [], {})
        for field in self.location_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", " \t\n"):
                with self.subTest(field=field, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, field: value})
            event = self.decode({**self.payload, field: " adl "})
            self.assertEqual(getattr(event, field), LocationCode("ADL"))
            self.assertEqual(self.codec.encode(event)[field], "ADL")

    def test_rejects_wrong_position_kind_types(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "position_kind"):
                self.decode({**self.payload, "position_kind": value})

    def test_rejects_unknown_position_kinds_case_changes_and_whitespace(self) -> None:
        values = ["", "unknown"]
        values.extend(kind.value.lower() for kind in RoutePositionKind)
        values.extend(f" {kind.value} " for kind in RoutePositionKind)
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decode({**self.payload, "position_kind": value})

    def test_preserves_unchanged_location_when_clearing_transit_target(self) -> None:
        payload = {
            **self.payload,
            "new_location": "SYD",
            "new_in_transit_to": None,
            "position_kind": RoutePositionKind.AT_STOP.value,
        }
        event = self.decode(payload)
        self.assertEqual(event.previous_location, event.new_location)
        self.assertEqual(event.previous_in_transit_to, LocationCode("BNE"))
        self.assertIsNone(event.new_in_transit_to)
        self.assertEqual(self.codec.encode(event), payload)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["new_location"] = None
        self.assertEqual(event.new_location, LocationCode("MEL"))
        encoded = self.codec.encode(event)
        encoded["previous_in_transit_to"] = None
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_one_without_conflicting_with_other_reconciliation_events(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteStateReconciled, RouteStateReconciledEventPayloadCodec())
        registry.register(PackageStateReconciled, PackageStateReconciledEventPayloadCodec())
        registry.register(TruckPositionReconciled, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("truck_position_reconciled", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, TruckPositionReconciled)
        self.assertEqual(adapter.event_version, TruckPositionReconciled.event_version)
        for name in ("route_state_reconciled", "package_state_reconciled"):
            self.assertIsNot(adapter, registry.for_identity(name, 1))
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("truck_position_reconciled", version)

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
                    "event_id": EVENT_ID, "occurred_at": OCCURRED_AT, "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )


class PackageStateReconciledCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = PackageStateReconciledEventPayloadCodec()
        self.previous_arrival = COMPLETION - timedelta(hours=2)
        self.new_arrival = COMPLETION - timedelta(hours=1)
        self.reasons = (
            PackageReconciliationReason.LIFECYCLE_STATE_INCONSISTENT,
            PackageReconciliationReason.EXPECTED_ARRIVAL_RECALCULATED,
        )
        self.payload: JSONObject = {
            "package_id": 7,
            "route_id": 19,
            "previous_status": ItemStatus.DONE.value,
            "new_status": ItemStatus.IN_PROGRESS.value,
            "previous_location": "MEL",
            "new_location": "SYD",
            "previous_expected_arrival": self.previous_arrival.isoformat(),
            "new_expected_arrival": self.new_arrival.isoformat(),
            "scheduled_pickup_time": DEPARTURE.isoformat(),
            "scheduled_delivery_time": COMPLETION.isoformat(),
            "reasons": [reason.value for reason in self.reasons],
        }
        self.timestamp_fields = (
            "previous_expected_arrival", "new_expected_arrival",
            "scheduled_pickup_time", "scheduled_delivery_time",
        )

    def decode(self, payload: JSONObject) -> PackageStateReconciled:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_all_nullable_combinations(self) -> None:
        for route_id, previous_arrival, new_arrival, pickup, delivery in product(
            (None, 19), (None, self.previous_arrival), (None, self.new_arrival),
            (None, DEPARTURE), (None, COMPLETION),
        ):
            with self.subTest(
                route=route_id, previous=previous_arrival, new=new_arrival, pickup=pickup, delivery=delivery
            ):
                event = PackageStateReconciled(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    package_id=7,
                    route_id=route_id,
                    previous_status=ItemStatus.DONE,
                    new_status=ItemStatus.IN_PROGRESS,
                    previous_location=LocationCode("MEL"),
                    new_location=LocationCode("SYD"),
                    previous_expected_arrival=previous_arrival,
                    new_expected_arrival=new_arrival,
                    scheduled_pickup_time=pickup,
                    scheduled_delivery_time=delivery,
                    reasons=self.reasons,
                )
                expected = dict(self.payload)
                expected["route_id"] = route_id
                for field, value in zip(
                    self.timestamp_fields, (previous_arrival, new_arrival, pickup, delivery), strict=True
                ):
                    expected[field] = value.isoformat() if value is not None else None
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                self.assertIs(type(encoded["package_id"]), int)
                self.assertIs(type(encoded["route_id"]), type(route_id))
                for field in (
                    "previous_status", "new_status", "previous_location", "new_location", *self.timestamp_fields
                ):
                    if encoded[field] is not None:
                        self.assertIs(type(encoded[field]), str)
                self.assertIs(type(encoded["reasons"]), list)
                for reason in cast(list[JSONValue], encoded["reasons"]):
                    self.assertIs(type(reason), str)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), PackageStateReconciled)
                self.assertEqual(restored, event)
                self.assertIs(restored.previous_status, ItemStatus.DONE)
                self.assertIs(restored.new_status, ItemStatus.IN_PROGRESS)
                self.assertIsInstance(restored.previous_location, LocationCode)
                self.assertIsInstance(restored.new_location, LocationCode)
                self.assertIs(type(restored.reasons), tuple)
                for actual, reason in zip(restored.reasons, self.reasons, strict=True):
                    self.assertIs(actual, reason)

    def test_round_trips_every_single_reason_and_preserves_multiple_reason_order(self) -> None:
        cases: list[tuple[PackageReconciliationReason, ...]] = [
            (reason,) for reason in PackageReconciliationReason
        ]
        cases.append(tuple(reversed(PackageReconciliationReason)))
        for reasons in cases:
            with self.subTest(reasons=reasons):
                payload: JSONObject = {**self.payload, "reasons": [reason.value for reason in reasons]}
                event = self.decode(payload)
                self.assertEqual(event.reasons, reasons)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_empty_and_duplicate_reasons(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one reason"):
            self.decode({**self.payload, "reasons": []})
        for reason in PackageReconciliationReason:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, "must be unique"):
                self.decode({**self.payload, "reasons": [reason.value, reason.value]})
        with self.assertRaisesRegex(ValueError, "must be unique"):
            self.decode({**self.payload, "reasons": [r.value for r in (*self.reasons, self.reasons[0])]})

    def test_requires_every_key_including_nullable_fields(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_singular_reason_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "reason", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_validates_required_and_optional_ids_without_coercion(self) -> None:
        values: tuple[JSONValue, ...] = (True, False, 1.0, "7", "", [], {})
        for field in ("package_id", "route_id"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 2**63):
                with self.subTest(field=field, value=value):
                    self.assertEqual(getattr(self.decode({**self.payload, field: value}), field), value)
        with self.assertRaisesRegex(TypeError, "package_id"):
            self.decode({**self.payload, "package_id": None})

    def test_preserves_status_values_without_reapplying_reconciliation_rules(self) -> None:
        for previous_status, new_status in product(ItemStatus, repeat=2):
            with self.subTest(previous_status=previous_status, new_status=new_status):
                payload = {
                    **self.payload, "previous_status": previous_status.value, "new_status": new_status.value
                }
                event = self.decode(payload)
                self.assertIs(event.previous_status, previous_status)
                self.assertIs(event.new_status, new_status)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_invalid_statuses(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_status", "new_status"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", "unknown", "TODO", "IN_PROGRESS", "DONE", " In Progress "):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, field: value})

    def test_validates_and_normalizes_both_locations(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_location", "new_location"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("", " \t\n"):
                with self.subTest(field=field, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, field: value})
            self.assertEqual(getattr(self.decode({**self.payload, field: " bne "}), field), LocationCode("BNE"))

    def test_requires_reasons_to_be_a_list(self) -> None:
        values: tuple[object, ...] = (
            None, True, 1, 1.5, {}, "route_unscheduled", ("route_unscheduled",), {"route_unscheduled"},
        )
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "reasons"):
                self.decode({**self.payload, "reasons": cast(JSONValue, value)})

    def test_rejects_non_string_reason_elements_with_correct_index(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for index in range(2):
            for value in values:
                reasons: list[JSONValue] = [reason.value for reason in self.reasons]
                reasons[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaisesRegex(TypeError, rf"reasons\[{index}\]"),
                ):
                    self.decode({**self.payload, "reasons": reasons})

    def test_rejects_unknown_reason_values_member_names_and_whitespace(self) -> None:
        values = ["", "unknown", *(reason.name for reason in PackageReconciliationReason)]
        values.extend(f" {reason.value} " for reason in PackageReconciliationReason)
        for index in range(2):
            for value in values:
                reasons: list[JSONValue] = [reason.value for reason in self.reasons]
                reasons[index] = value
                with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, "reasons": reasons})

    def test_rejects_non_string_timestamps_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, COMPLETION)
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

    def test_payload_and_reasons_list_are_not_mutated_or_retained(self) -> None:
        original = cast(JSONObject, json.loads(json.dumps(self.payload)))
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        cast(list[JSONValue], self.payload["reasons"]).clear()
        self.assertEqual(event.reasons, self.reasons)
        encoded = self.codec.encode(event)
        cast(list[JSONValue], encoded["reasons"]).reverse()
        encoded["route_id"] = None
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_one_without_conflicting_with_route_reconciliation(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteStateReconciled, RouteStateReconciledEventPayloadCodec())
        registry.register(PackageStateReconciled, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("package_state_reconciled", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, PackageStateReconciled)
        self.assertEqual(adapter.event_version, PackageStateReconciled.event_version)
        self.assertIsNot(adapter, registry.for_identity("route_state_reconciled", 1))
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("package_state_reconciled", version)

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
                    "event_id": EVENT_ID, "occurred_at": OCCURRED_AT, "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )


class RouteStateReconciledCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = RouteStateReconciledEventPayloadCodec()
        self.payload: JSONObject = {
            "route_id": 19,
            "previous_status": RouteStatus.IN_PROGRESS.value,
            "new_status": RouteStatus.SCHEDULED.value,
            "departure_time": DEPARTURE.isoformat(),
            "expected_completion_time": COMPLETION.isoformat(),
            "reason": RouteReconciliationReason.BEFORE_SCHEDULED_DEPARTURE.value,
        }
        self.timestamp_fields = ("departure_time", "expected_completion_time")

    def decode(self, payload: JSONObject) -> RouteStateReconciled:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_every_reason_and_nullable_combination(self) -> None:
        for reason, departure, completion in product(
            RouteReconciliationReason, (None, DEPARTURE), (None, COMPLETION)
        ):
            with self.subTest(reason=reason, departure=departure, completion=completion):
                event = RouteStateReconciled(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    route_id=19,
                    previous_status=RouteStatus.IN_PROGRESS,
                    new_status=RouteStatus.SCHEDULED,
                    departure_time=departure,
                    expected_completion_time=completion,
                    reason=reason,
                )
                expected = dict(self.payload)
                expected.update(
                    departure_time=departure.isoformat() if departure is not None else None,
                    expected_completion_time=completion.isoformat() if completion is not None else None,
                    reason=reason.value,
                )
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                self.assertIs(type(encoded["route_id"]), int)
                for field in ("previous_status", "new_status", "reason", *self.timestamp_fields):
                    if encoded[field] is not None:
                        self.assertIs(type(encoded[field]), str)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), RouteStateReconciled)
                self.assertEqual(restored, event)
                self.assertIs(restored.reason, reason)
                self.assertIs(restored.previous_status, RouteStatus.IN_PROGRESS)
                self.assertIs(restored.new_status, RouteStatus.SCHEDULED)

    def test_preserves_status_values_without_reapplying_reconciliation_rules(self) -> None:
        for previous_status, new_status in product(RouteStatus, repeat=2):
            with self.subTest(previous_status=previous_status, new_status=new_status):
                payload = {
                    **self.payload, "previous_status": previous_status.value, "new_status": new_status.value
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

    def test_rejects_unknown_plural_reason_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "reasons", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"
        ):
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
            for value in ("unknown", "", "scheduled", " SCHEDULED ", "In Progress"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, field: value})

    def test_rejects_wrong_reason_types_and_reason_lists(self) -> None:
        values: tuple[JSONValue, ...] = (
            None, True, False, 1, 1.5, [], {}, [RouteReconciliationReason.MISSING_DEPARTURE_TIME.value],
        )
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "reason"):
                self.decode({**self.payload, "reason": value})

    def test_rejects_reason_member_names_unknown_values_and_whitespace(self) -> None:
        for value in ("", "unknown", *(reason.name for reason in RouteReconciliationReason)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decode({**self.payload, "reason": value})
        for reason in RouteReconciliationReason:
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                self.decode({**self.payload, "reason": f" {reason.value} "})

    def test_rejects_non_string_schedule_timestamps(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, DEPARTURE)
        for field in self.timestamp_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_schedule_timestamps(self) -> None:
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
        self.payload["departure_time"] = None
        self.assertEqual(event.departure_time, DEPARTURE)
        encoded = self.codec.encode(event)
        encoded["reason"] = RouteReconciliationReason.MISSING_DEPARTURE_TIME.value
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_one_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteStateReconciled, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("route_state_reconciled", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, RouteStateReconciled)
        self.assertEqual(adapter.event_version, RouteStateReconciled.event_version)
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("route_state_reconciled", version)

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
