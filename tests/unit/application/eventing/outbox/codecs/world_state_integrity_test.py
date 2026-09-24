"""World-state snapshot corruption and quarantine outbox payload contract tests."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.eventing.outbox.codecs.world_state_integrity import (
    WorldStateCorruptionDetectedEventPayloadCodec,
    WorldStateSnapshotQuarantinedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.world_state_transfer import WorldStateImportFailedEventPayloadCodec
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.world_state_events import (
    WorldStateCorruptionDetected,
    WorldStateImportFailed,
    WorldStateSnapshotQuarantined,
)
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")


OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)


RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)


class WorldStateSnapshotQuarantinedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = WorldStateSnapshotQuarantinedEventPayloadCodec()
        self.payload: JSONObject = {
            "original_path": "data/world.json",
            "quarantined_path": "data/world.json.corrupt",
            "reason": "MALFORMED_JSON",
        }

    def decode(self, payload: JSONObject) -> WorldStateSnapshotQuarantined:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_and_json_round_trip_for_all_corruption_reasons(self) -> None:
        for reason in WorldStateCorruptionReason:
            with self.subTest(reason=reason):
                event = WorldStateSnapshotQuarantined(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    original_path="data/world.json",
                    quarantined_path="data/world.json.corrupt",
                    reason=reason,
                )
                expected: JSONObject = {
                    "original_path": "data/world.json",
                    "quarantined_path": "data/world.json.corrupt",
                    "reason": reason.value,
                }
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                for field in expected:
                    self.assertIs(type(encoded[field]), str)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), WorldStateSnapshotQuarantined)
                self.assertEqual(restored, event)
                self.assertIs(restored.reason, reason)
                self.assertEqual(restored.event_version, 1)
                self.assertEqual(self.codec.event_version, 1)

    def test_requires_every_key(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_snapshot_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "snapshot_path", "schema_version", "event_id", "event_version",
            "occurred_at", "recorded_at", "envelope_id",
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_rejects_non_string_paths_and_reasons(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for field in self.payload:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})

    def test_preserves_each_path_independently_without_normalization_or_filesystem_lookup(self) -> None:
        for field in ("original_path", "quarantined_path"):
            for path in ("", " \t\n", " data/world.json ", "missing/snapshot.json", r"C:\snapshots\world.json"):
                with self.subTest(field=field, path=path):
                    payload = {**self.payload, field: path}
                    event = self.decode(payload)
                    self.assertEqual(event.original_path, payload["original_path"])
                    self.assertEqual(event.quarantined_path, payload["quarantined_path"])
                    self.assertEqual(self.codec.encode(event), payload)

    def test_rejects_unknown_or_normalized_reason_strings(self) -> None:
        for reason in ("", " ", "UNKNOWN", "malformed_json", " MALFORMED_JSON "):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                self.decode({**self.payload, "reason": reason})

    def test_distinguishes_corruption_from_operation_failure_reasons(self) -> None:
        for failure_reason in WorldStateFailureReason:
            with self.subTest(reason=failure_reason):
                payload = {**self.payload, "reason": failure_reason.value}
                if failure_reason is WorldStateFailureReason.UNSUPPORTED_SCHEMA:
                    event = self.decode(payload)
                    self.assertIs(event.reason, WorldStateCorruptionReason.UNSUPPORTED_SCHEMA)
                else:
                    with self.assertRaises(ValueError):
                        self.decode(payload)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["original_path"] = "other.json"
        self.payload["quarantined_path"] = "other.json.corrupt"
        self.assertEqual(event.original_path, "data/world.json")
        self.assertEqual(event.quarantined_path, "data/world.json.corrupt")
        encoded = self.codec.encode(event)
        encoded["reason"] = "INVALID_STRUCTURE"
        self.assertIs(event.reason, WorldStateCorruptionReason.MALFORMED_JSON)
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_one_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(WorldStateSnapshotQuarantined, self.codec)
        registry.register(WorldStateCorruptionDetected, WorldStateCorruptionDetectedEventPayloadCodec())
        event = self.decode(self.payload)
        adapter = registry.for_identity("world_state_snapshot_quarantined", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, WorldStateSnapshotQuarantined)
        self.assertEqual(adapter.event_version, WorldStateSnapshotQuarantined.event_version)
        self.assertIsNot(adapter, registry.for_identity("world_state_corruption_detected", 1))
        restored = adapter.decode(
            registry.for_event(event).encode(event),
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
        )
        self.assertIs(type(restored), WorldStateSnapshotQuarantined)
        self.assertEqual(restored, event)
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("world_state_snapshot_quarantined", version)

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


class WorldStateCorruptionDetectedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = WorldStateCorruptionDetectedEventPayloadCodec()
        self.payload: JSONObject = {
            "snapshot_path": "data/world.json",
            "reason": "MALFORMED_JSON",
        }

    def decode(self, payload: JSONObject) -> WorldStateCorruptionDetected:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_and_json_round_trip_for_all_corruption_reasons(self) -> None:
        for reason in WorldStateCorruptionReason:
            with self.subTest(reason=reason):
                event = WorldStateCorruptionDetected(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    snapshot_path="data/world.json",
                    reason=reason,
                )
                expected: JSONObject = {"snapshot_path": "data/world.json", "reason": reason.value}
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                self.assertIs(type(encoded["reason"]), str)
                self.assertIs(type(encoded["snapshot_path"]), str)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), WorldStateCorruptionDetected)
                self.assertEqual(restored, event)
                self.assertIs(restored.reason, reason)
                self.assertEqual(restored.event_version, 1)
                self.assertEqual(self.codec.event_version, 1)

    def test_requires_every_key(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_schema_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "schema_version", "event_id", "event_version",
            "occurred_at", "recorded_at", "envelope_id",
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

    def test_rejects_unknown_or_normalized_reason_strings(self) -> None:
        for reason in ("", " ", "UNKNOWN", "malformed_json", " MALFORMED_JSON "):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                self.decode({**self.payload, "reason": reason})

    def test_distinguishes_corruption_from_operation_failure_reasons(self) -> None:
        for failure_reason in WorldStateFailureReason:
            with self.subTest(reason=failure_reason):
                payload = {**self.payload, "reason": failure_reason.value}
                if failure_reason is WorldStateFailureReason.UNSUPPORTED_SCHEMA:
                    event = self.decode(payload)
                    self.assertIs(event.reason, WorldStateCorruptionReason.UNSUPPORTED_SCHEMA)
                else:
                    with self.assertRaises(ValueError):
                        self.decode(payload)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["snapshot_path"] = "other.json"
        self.assertEqual(event.snapshot_path, "data/world.json")
        encoded = self.codec.encode(event)
        encoded["reason"] = "INVALID_STRUCTURE"
        self.assertIs(event.reason, WorldStateCorruptionReason.MALFORMED_JSON)
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_event_version_one_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(WorldStateCorruptionDetected, self.codec)
        registry.register(WorldStateImportFailed, WorldStateImportFailedEventPayloadCodec())
        event = self.decode(self.payload)
        adapter = registry.for_identity("world_state_corruption_detected", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, WorldStateCorruptionDetected)
        self.assertEqual(adapter.event_version, WorldStateCorruptionDetected.event_version)
        self.assertIsNot(adapter, registry.for_identity("world_state_import_failed", 1))
        restored = adapter.decode(
            registry.for_event(event).encode(event),
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
        )
        self.assertIs(type(restored), WorldStateCorruptionDetected)
        self.assertEqual(restored, event)
        for version in (2, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("world_state_corruption_detected", version)

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
