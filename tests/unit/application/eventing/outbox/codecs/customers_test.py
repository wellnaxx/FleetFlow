"""Customer-created outbox payload contract tests."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

from src.application.eventing.outbox.codecs.customers import CustomerCreatedEventPayloadCodec
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.domain.events.customer_events import CustomerCreated
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)


class CustomerCreatedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = CustomerCreatedEventPayloadCodec()

    def decode(self, payload: JSONObject) -> CustomerCreated:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_and_json_round_trip_preserve_identity_and_metadata(self) -> None:
        for customer_id in (1, 7, 2**63):
            with self.subTest(customer_id=customer_id):
                event = CustomerCreated(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    customer_id=customer_id,
                )
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, {"customer_id": customer_id})
                self.assertIs(type(encoded["customer_id"]), int)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded))))
                self.assertIs(type(restored), CustomerCreated)
                self.assertEqual(restored, event)

    def test_requires_customer_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing fields:.*customer_id"):
            self.decode({})

    def test_rejects_extra_contact_details_and_metadata(self) -> None:
        for field in ("name", "email", "phone", "event_id", "actor_user_id", "user_id"):
            with self.subTest(field=field):
                payload: JSONObject = {"customer_id": 7, field: "unexpected"}
                with self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                    self.decode(payload)

    def test_rejects_non_positive_customer_ids(self) -> None:
        for value in (0, -1, -(2**63)):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "customer_id must be a positive integer"),
            ):
                self.decode({"customer_id": value})

    def test_rejects_wrong_customer_id_types_without_coercion(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1.0, "7", "", [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "customer_id"):
                self.decode({"customer_id": value})

    def test_payload_and_event_remain_independent(self) -> None:
        payload: JSONObject = {"customer_id": 7}
        event = self.decode(payload)
        self.assertEqual(payload, {"customer_id": 7})
        payload["customer_id"] = 999
        self.assertEqual(event.customer_id, 7)
        encoded = self.codec.encode(event)
        encoded["customer_id"] = 100
        self.assertEqual(self.codec.encode(event), {"customer_id": 7})

    def test_registry_resolves_exact_identity_and_rejects_other_versions(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(CustomerCreated, self.codec)
        event = self.decode({"customer_id": 7})
        adapter = registry.for_identity("customer_created", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, CustomerCreated)
        self.assertEqual(adapter.event_version, 1)
        self.assertEqual(
            adapter.decode(
                adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            ),
            event,
        )
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("customer_created", 2)

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
                        {"customer_id": 7},
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )
