"""Reconciliation outbox payload serialization and validation contracts."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from itertools import product
from typing import cast
from uuid import UUID

from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
from src.application.eventing.outbox.codecs.reconciliation import RouteStateReconciledEventPayloadCodec
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.reconciliation_events import RouteStateReconciled
from src.domain.enums.route_status import RouteStatus
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)
DEPARTURE = datetime(2030, 1, 3, 6, 30, 45, 123456)
COMPLETION = datetime(2030, 1, 4, 18, 45, 30, 654321)


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
