"""Fleet-seeded outbox payload serialization and validation contracts."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from itertools import product
from typing import cast
from uuid import UUID

from src.application.eventing.outbox.codecs.startup import FleetSeededEventPayloadCodec
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.startup_events import FleetSeeded
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)


class FleetSeededCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = FleetSeededEventPayloadCodec()
        self.payload: JSONObject = {"seeded_truck_ids": [1003, 1001, 1040], "backend": "memory"}

    def decode(self, payload: JSONObject) -> FleetSeeded:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_and_json_round_trip_preserve_ids_and_derived_count(self) -> None:
        id_cases: tuple[tuple[int, ...], ...] = (
            (), (1001,), (1003, 1001, 1040), tuple(range(1001, 1041)), (1, 1041, 2**63), (1001, 1001),
        )
        for ids, backend in product(id_cases, ("memory", "postgres")):
            with self.subTest(ids=ids, backend=backend):
                event = FleetSeeded(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    seeded_truck_ids=ids,
                    backend=backend,
                )
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, {"seeded_truck_ids": list(ids), "backend": backend})
                self.assertIs(type(encoded["seeded_truck_ids"]), list)
                self.assertIs(type(encoded["backend"]), str)
                for truck_id in cast(list[JSONValue], encoded["seeded_truck_ids"]):
                    self.assertIs(type(truck_id), int)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), FleetSeeded)
                self.assertEqual(restored, event)
                self.assertIs(type(restored.seeded_truck_ids), tuple)
                self.assertEqual(restored.truck_count, len(ids))

    def test_requires_every_key(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_derived_count_unknown_and_metadata_keys(self) -> None:
        for field in (
            "truck_count", "unknown", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_requires_id_list_instead_of_other_containers_or_scalars(self) -> None:
        values: tuple[object, ...] = (None, True, 1001, 1001.0, "1001", {}, (1001,), {1001})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "seeded_truck_ids"):
                self.decode({**self.payload, "seeded_truck_ids": cast(JSONValue, value)})

    def test_rejects_non_integer_ids_with_correct_index(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1001.0, "1001", "", [], {})
        for index in range(3):
            for value in values:
                ids: list[JSONValue] = [1003, 1001, 1040]
                ids[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaisesRegex(TypeError, rf"seeded_truck_ids\[{index}\]"),
                ):
                    self.decode({**self.payload, "seeded_truck_ids": ids})

    def test_rejects_non_positive_ids_with_correct_index(self) -> None:
        for index in range(3):
            for value in (0, -1, -(2**63)):
                ids: list[JSONValue] = [1003, 1001, 1040]
                ids[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaisesRegex(ValueError, rf"seeded_truck_ids\[{index}\]"),
                ):
                    self.decode({**self.payload, "seeded_truck_ids": ids})

    def test_accepts_ids_inside_and_outside_seeded_fleet_range(self) -> None:
        for truck_id in (1, 1000, 1001, 1040, 1041, 2**63):
            with self.subTest(truck_id=truck_id):
                event = self.decode({**self.payload, "seeded_truck_ids": [truck_id]})
                self.assertEqual(event.seeded_truck_ids, (truck_id,))
                self.assertEqual(event.truck_count, 1)

    def test_rejects_non_string_backends(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "backend"):
                self.decode({**self.payload, "backend": value})

    def test_preserves_backend_text_without_normalization_or_configuration_lookup(self) -> None:
        for backend in ("", " \t\n", " POSTGRES ", "custom_backend"):
            with self.subTest(backend=backend):
                payload = {**self.payload, "backend": backend}
                event = self.decode(payload)
                self.assertEqual(event.backend, backend)
                self.assertEqual(self.codec.encode(event), payload)

    def test_payload_and_id_list_are_not_mutated_or_retained(self) -> None:
        original = cast(JSONObject, json.loads(json.dumps(self.payload)))
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        cast(list[JSONValue], self.payload["seeded_truck_ids"]).clear()
        self.payload["backend"] = "postgres"
        self.assertEqual(event.seeded_truck_ids, (1003, 1001, 1040))
        self.assertEqual(event.truck_count, 3)
        self.assertEqual(event.backend, "memory")
        encoded = self.codec.encode(event)
        cast(list[JSONValue], encoded["seeded_truck_ids"]).append(9999)
        self.assertEqual(event.truck_count, 3)
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(FleetSeeded, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("fleet_seeded", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, FleetSeeded)
        self.assertEqual(adapter.event_version, FleetSeeded.event_version)
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("fleet_seeded", version)

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
