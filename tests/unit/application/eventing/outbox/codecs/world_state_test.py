"""World-state outbox payload serialization and validation contracts."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.eventing.outbox.codecs.world_state import (
    WorldStateExportedEventPayloadCodec,
    WorldStateExportFailedEventPayloadCodec,
    WorldStateImportedEventPayloadCodec,
    WorldStateImportFailedEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.world_state_events import (
    WorldStateExported,
    WorldStateExportFailed,
    WorldStateImported,
    WorldStateImportFailed,
)
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)


class WorldStateExportedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = WorldStateExportedEventPayloadCodec()
        self.payload: JSONObject = {
            "snapshot_path": "data/world.json",
            "schema_version": 3,
            "customer_count": 2,
            "package_count": 7,
            "route_count": 4,
            "truck_count": 40,
        }
        self.count_fields = ("customer_count", "package_count", "route_count", "truck_count")
        self.count_attributes = ("customers", "packages", "routes", "trucks")

    def decode(self, payload: JSONObject) -> WorldStateExported:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_flat_wire_contract_and_json_round_trip(self) -> None:
        for counts in (
            WorldStateEntityCounts(customers=2, packages=7, routes=4, trucks=40),
            WorldStateEntityCounts(customers=0, packages=0, routes=0, trucks=0),
        ):
            with self.subTest(counts=counts):
                event = WorldStateExported(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    snapshot_path="data/world.json",
                    schema_version=3,
                    entity_counts=counts,
                )
                expected: JSONObject = {
                    "snapshot_path": "data/world.json",
                    "schema_version": 3,
                    "customer_count": counts.customers,
                    "package_count": counts.packages,
                    "route_count": counts.routes,
                    "truck_count": counts.trucks,
                }
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                self.assertIs(type(encoded["snapshot_path"]), str)
                for field in ("schema_version", *self.count_fields):
                    self.assertIs(type(encoded[field]), int)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), WorldStateExported)
                self.assertEqual(restored, event)
                self.assertIs(type(restored.entity_counts), WorldStateEntityCounts)
                self.assertIsNot(restored.entity_counts, counts)

    def test_requires_every_key(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_nested_counts_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "entity_counts", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_rejects_non_string_paths(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "snapshot_path"):
                self.decode({**self.payload, "snapshot_path": value})

    def test_preserves_path_text_without_normalization_or_filesystem_lookup(self) -> None:
        for path in ("", " \t\n", " data/world.json ", "missing/snapshot.json", r"C:\snapshots\world.json"):
            with self.subTest(path=path):
                payload = {**self.payload, "snapshot_path": path}
                event = self.decode(payload)
                self.assertEqual(event.snapshot_path, path)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_non_integer_counts_and_schema_versions_without_coercion(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1.0, "7", "", [], {}, float("nan"), float("inf"))
        for field in ("schema_version", *self.count_fields):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})

    def test_rejects_non_positive_schema_versions(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "schema_version"):
                self.decode({**self.payload, "schema_version": value})

    def test_snapshot_schema_version_is_independent_of_event_codec_version(self) -> None:
        for version in (1, 2, 3, 2**63):
            with self.subTest(version=version):
                payload = {**self.payload, "schema_version": version}
                event = self.decode(payload)
                self.assertEqual(event.schema_version, version)
                self.assertEqual(event.event_version, 1)
                self.assertEqual(self.codec.event_version, 1)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_negative_counts_independently(self) -> None:
        for field in self.count_fields:
            for value in (-1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_accepts_zero_and_large_counts_and_maps_each_to_correct_attribute(self) -> None:
        for field, attribute in zip(self.count_fields, self.count_attributes, strict=True):
            for value in (0, 1, 2**63):
                with self.subTest(field=field, value=value):
                    payload = {**self.payload, field: value}
                    event = self.decode(payload)
                    self.assertEqual(getattr(event.entity_counts, attribute), value)
                    self.assertEqual(self.codec.encode(event), payload)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["customer_count"] = 999
        self.assertEqual(event.entity_counts.customers, 2)
        encoded = self.codec.encode(event)
        encoded["truck_count"] = 0
        self.assertEqual(event.entity_counts.trucks, 40)
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_one_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(WorldStateExported, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("world_state_exported", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, WorldStateExported)
        self.assertEqual(adapter.event_version, WorldStateExported.event_version)
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("world_state_exported", version)

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


class WorldStateImportedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = WorldStateImportedEventPayloadCodec()
        self.payload: JSONObject = {
            "snapshot_path": "data/world.json",
            "schema_version": 3,
            "previous_customer_count": 2,
            "previous_package_count": 7,
            "previous_route_count": 4,
            "previous_truck_count": 40,
            "new_customer_count": 5,
            "new_package_count": 3,
            "new_route_count": 6,
            "new_truck_count": 20,
        }
        self.count_fields = (
            "previous_customer_count", "previous_package_count", "previous_route_count", "previous_truck_count",
            "new_customer_count", "new_package_count", "new_route_count", "new_truck_count",
        )

    def decode(self, payload: JSONObject) -> WorldStateImported:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_flat_wire_contract_and_json_round_trip(self) -> None:
        previous = WorldStateEntityCounts(customers=2, packages=7, routes=4, trucks=40)
        new = WorldStateEntityCounts(customers=5, packages=3, routes=6, trucks=20)
        event = WorldStateImported(
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
            snapshot_path="data/world.json",
            schema_version=3,
            previous_entity_counts=previous,
            new_entity_counts=new,
        )
        encoded = self.codec.encode(event)
        self.assertEqual(encoded, self.payload)
        self.assertIs(type(encoded["snapshot_path"]), str)
        for field in ("schema_version", *self.count_fields):
            self.assertIs(type(encoded[field]), int)
        restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
        self.assertIs(type(restored), WorldStateImported)
        self.assertEqual(restored, event)
        self.assertIs(type(restored.previous_entity_counts), WorldStateEntityCounts)
        self.assertIs(type(restored.new_entity_counts), WorldStateEntityCounts)
        self.assertIsNot(restored.previous_entity_counts, previous)
        self.assertIsNot(restored.new_entity_counts, new)
        self.assertIsNot(restored.previous_entity_counts, restored.new_entity_counts)

    def test_requires_every_key(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_nested_counts_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "entity_counts", "previous_entity_counts", "new_entity_counts",
            "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id",
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_rejects_non_string_paths(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "snapshot_path"):
                self.decode({**self.payload, "snapshot_path": value})

    def test_preserves_path_text_without_normalization_or_filesystem_lookup(self) -> None:
        for path in ("", " \t\n", " data/world.json ", "missing/snapshot.json", r"C:\snapshots\world.json"):
            with self.subTest(path=path):
                payload = {**self.payload, "snapshot_path": path}
                event = self.decode(payload)
                self.assertEqual(event.snapshot_path, path)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_non_integer_counts_and_schema_versions_without_coercion(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1.0, "7", "", [], {}, float("nan"), float("inf"))
        for field in ("schema_version", *self.count_fields):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})

    def test_rejects_non_positive_schema_versions(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "schema_version"):
                self.decode({**self.payload, "schema_version": value})

    def test_snapshot_schema_version_is_independent_of_event_codec_version(self) -> None:
        for version in (1, 2, 3, 2**63):
            with self.subTest(version=version):
                payload = {**self.payload, "schema_version": version}
                event = self.decode(payload)
                self.assertEqual(event.schema_version, version)
                self.assertEqual(event.event_version, 2)
                self.assertEqual(self.codec.event_version, 2)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_negative_counts_independently(self) -> None:
        for field in self.count_fields:
            for value in (-1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_accepts_zero_and_large_counts_and_maps_each_to_correct_snapshot(self) -> None:
        for prefix in ("previous", "new"):
            for singular, attribute in (
                ("customer", "customers"), ("package", "packages"), ("route", "routes"), ("truck", "trucks"),
            ):
                field = f"{prefix}_{singular}_count"
                for value in (0, 1, 2**63):
                    with self.subTest(field=field, value=value):
                        payload = {**self.payload, field: value}
                        event = self.decode(payload)
                        counts = (
                            event.previous_entity_counts if prefix == "previous" else event.new_entity_counts
                        )
                        self.assertEqual(getattr(counts, attribute), value)
                        self.assertEqual(self.codec.encode(event), payload)

    def test_accepts_empty_unchanged_increasing_and_decreasing_snapshots(self) -> None:
        for previous, new in ((0, 0), (5, 5), (0, 10), (10, 0)):
            with self.subTest(previous=previous, new=new):
                payload = dict(self.payload)
                for field in self.count_fields:
                    payload[field] = previous if field.startswith("previous_") else new
                event = self.decode(payload)
                self.assertEqual(
                    event.previous_entity_counts,
                    WorldStateEntityCounts(
                        customers=previous, packages=previous, routes=previous, trucks=previous
                    ),
                )
                self.assertEqual(
                    event.new_entity_counts,
                    WorldStateEntityCounts(customers=new, packages=new, routes=new, trucks=new),
                )
                self.assertEqual(self.codec.encode(event), payload)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["previous_customer_count"] = 999
        self.payload["new_customer_count"] = 888
        self.assertEqual(event.previous_entity_counts.customers, 2)
        self.assertEqual(event.new_entity_counts.customers, 5)
        encoded = self.codec.encode(event)
        encoded["previous_truck_count"] = 0
        encoded["new_truck_count"] = 0
        self.assertEqual(event.previous_entity_counts.trucks, 40)
        self.assertEqual(event.new_entity_counts.trucks, 20)
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(WorldStateImported, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("world_state_imported", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, WorldStateImported)
        self.assertEqual(adapter.event_version, WorldStateImported.event_version)
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("world_state_imported", version)

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


class WorldStateImportFailedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = WorldStateImportFailedEventPayloadCodec()
        self.payload: JSONObject = {
            "snapshot_path": "data/world.json",
            "schema_version": 3,
            "reason": "CORRUPT_SNAPSHOT",
        }

    def decode(self, payload: JSONObject) -> WorldStateImportFailed:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_and_json_round_trip_for_all_reasons_and_optional_versions(self) -> None:
        for reason in WorldStateFailureReason:
            for version in (None, 1, 2, 3, 2**63):
                with self.subTest(reason=reason, version=version):
                    event = WorldStateImportFailed(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        snapshot_path="data/world.json",
                        schema_version=version,
                        reason=reason,
                    )
                    expected: JSONObject = {
                        "snapshot_path": "data/world.json", "schema_version": version, "reason": reason.value,
                    }
                    encoded = self.codec.encode(event)
                    self.assertEqual(encoded, expected)
                    self.assertIs(type(encoded["reason"]), str)
                    self.assertIs(type(encoded["snapshot_path"]), str)
                    if version is None:
                        self.assertIsNone(encoded["schema_version"])
                    else:
                        self.assertIs(type(encoded["schema_version"]), int)
                    restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                    self.assertIs(type(restored), WorldStateImportFailed)
                    self.assertEqual(restored, event)
                    self.assertIs(restored.reason, reason)
                    self.assertEqual(restored.event_version, 1)
                    self.assertEqual(self.codec.event_version, 1)

    def test_requires_every_key_even_when_schema_version_is_unknown(self) -> None:
        for version in (None, 3):
            for field in self.payload:
                with self.subTest(version=version, field=field):
                    payload = {**self.payload, "schema_version": version}
                    del payload[field]
                    with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                        self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "entity_counts", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_rejects_non_string_paths_and_reasons(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for field in ("snapshot_path", "reason"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})

    def test_preserves_path_text_without_normalization_or_filesystem_lookup(self) -> None:
        for path in ("", " \t\n", " data/world.json ", "missing/snapshot.json", r"C:\snapshots\world.json"):
            with self.subTest(path=path):
                payload = {**self.payload, "snapshot_path": path}
                event = self.decode(payload)
                self.assertEqual(event.snapshot_path, path)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_non_integer_schema_versions_without_coercion(self) -> None:
        values: tuple[JSONValue, ...] = (True, False, 1.0, "3", "", [], {}, float("nan"), float("inf"))
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "schema_version"):
                self.decode({**self.payload, "schema_version": value})

    def test_rejects_non_positive_schema_versions(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "schema_version"):
                self.decode({**self.payload, "schema_version": value})

    def test_rejects_unknown_or_normalized_reason_strings(self) -> None:
        for reason in ("", " ", "UNKNOWN", "corrupt_snapshot", " CORRUPT_SNAPSHOT "):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                self.decode({**self.payload, "reason": reason})

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["schema_version"] = None
        self.assertEqual(event.schema_version, 3)
        encoded = self.codec.encode(event)
        encoded["reason"] = "INVALID_PATH"
        self.assertIs(event.reason, WorldStateFailureReason.CORRUPT_SNAPSHOT)
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_one_without_confusing_import_or_export_events(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(WorldStateImportFailed, self.codec)
        registry.register(WorldStateExportFailed, WorldStateExportFailedEventPayloadCodec())
        registry.register(WorldStateImported, WorldStateImportedEventPayloadCodec())
        adapter = registry.for_identity("world_state_import_failed", 1)
        self.assertIs(adapter.event_class, WorldStateImportFailed)
        self.assertEqual(adapter.event_version, WorldStateImportFailed.event_version)
        self.assertIsNot(adapter, registry.for_identity("world_state_export_failed", 1))
        self.assertIsNot(adapter, registry.for_identity("world_state_imported", 2))
        for version in (None, 3):
            with self.subTest(version=version):
                event = self.decode({**self.payload, "schema_version": version})
                self.assertIs(adapter, registry.for_event(event))
                restored = adapter.decode(
                    adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
                )
                self.assertIs(type(restored), WorldStateImportFailed)
                self.assertEqual(restored, event)
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("world_state_import_failed", version)

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


class WorldStateExportFailedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = WorldStateExportFailedEventPayloadCodec()
        self.payload: JSONObject = {
            "snapshot_path": "data/world.json",
            "schema_version": 3,
            "reason": "PERSISTENCE_FAILURE",
        }

    def decode(self, payload: JSONObject) -> WorldStateExportFailed:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_and_json_round_trip_for_all_reasons_and_optional_versions(self) -> None:
        for reason in WorldStateFailureReason:
            for version in (None, 1, 3, 2**63):
                with self.subTest(reason=reason, version=version):
                    event = WorldStateExportFailed(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        snapshot_path="data/world.json",
                        schema_version=version,
                        reason=reason,
                    )
                    expected: JSONObject = {
                        "snapshot_path": "data/world.json", "schema_version": version, "reason": reason.value,
                    }
                    encoded = self.codec.encode(event)
                    self.assertEqual(encoded, expected)
                    self.assertIs(type(encoded["reason"]), str)
                    self.assertIs(type(encoded["snapshot_path"]), str)
                    restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                    self.assertIs(type(restored), WorldStateExportFailed)
                    self.assertEqual(restored, event)
                    self.assertIs(restored.reason, reason)
                    self.assertEqual(restored.event_version, 1)
                    self.assertEqual(self.codec.event_version, 1)

    def test_requires_every_key_even_when_schema_version_is_unknown(self) -> None:
        for version in (None, 3):
            for field in self.payload:
                with self.subTest(version=version, field=field):
                    payload = {**self.payload, "schema_version": version}
                    del payload[field]
                    with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                        self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "entity_counts", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_rejects_non_string_paths_and_reasons(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for field in ("snapshot_path", "reason"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})

    def test_preserves_path_text_without_normalization_or_filesystem_lookup(self) -> None:
        for path in ("", " \t\n", " data/world.json ", "missing/snapshot.json", r"C:\snapshots\world.json"):
            with self.subTest(path=path):
                payload = {**self.payload, "snapshot_path": path}
                event = self.decode(payload)
                self.assertEqual(event.snapshot_path, path)
                self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_non_integer_schema_versions_without_coercion(self) -> None:
        values: tuple[JSONValue, ...] = (True, False, 1.0, "3", "", [], {}, float("nan"), float("inf"))
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "schema_version"):
                self.decode({**self.payload, "schema_version": value})

    def test_rejects_non_positive_schema_versions(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "schema_version"):
                self.decode({**self.payload, "schema_version": value})

    def test_rejects_unknown_or_normalized_reason_strings(self) -> None:
        for reason in ("", " ", "UNKNOWN", "persistence_failure", " PERSISTENCE_FAILURE "):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                self.decode({**self.payload, "reason": reason})

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["schema_version"] = None
        self.assertEqual(event.schema_version, 3)
        encoded = self.codec.encode(event)
        encoded["reason"] = "INVALID_PATH"
        self.assertIs(event.reason, WorldStateFailureReason.PERSISTENCE_FAILURE)
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_one_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(WorldStateExportFailed, self.codec)
        registry.register(WorldStateExported, WorldStateExportedEventPayloadCodec())
        adapter = registry.for_identity("world_state_export_failed", 1)
        self.assertIs(adapter.event_class, WorldStateExportFailed)
        self.assertEqual(adapter.event_version, WorldStateExportFailed.event_version)
        self.assertIsNot(adapter, registry.for_identity("world_state_exported", 1))
        for version in (None, 3):
            with self.subTest(version=version):
                event = self.decode({**self.payload, "schema_version": version})
                self.assertIs(adapter, registry.for_event(event))
                self.assertEqual(
                    adapter.decode(
                        adapter.encode(event),
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                    ),
                    event,
                )
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("world_state_export_failed", version)

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
