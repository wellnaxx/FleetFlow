"""Customer-created outbox payload contract tests."""

import unittest
from unittest.mock import patch

from src.application.eventing.outbox.codecs.customers import CustomerCreatedEventPayloadCodec
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.domain.events.customer_events import CustomerCreated
from src.shared.json_types import JSONObject, JSONValue
from src.shared.json_validation import require_json_object_keys
from tests.unit.application.eventing.outbox.codecs.helpers import (
    EVENT_ID,
    OCCURRED_AT,
    RECORDED_AT,
    assert_invalid_metadata,
    decode_payload,
    json_round_trip,
)


class CustomerCreatedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = CustomerCreatedEventPayloadCodec()

    def decode(self, payload: JSONObject) -> CustomerCreated:
        return decode_payload(self.codec, payload)

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
                restored = self.decode(json_round_trip(encoded))
                self.assertIs(type(restored), CustomerCreated)
                self.assertEqual(restored, event)

    def test_requires_customer_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing fields:.*customer_id"):
            self.decode({})

    def test_reuses_immutable_payload_keys_across_calls_and_codec_instances(self) -> None:
        captured: list[frozenset[str]] = []

        def validate(payload: JSONObject, expected_keys: frozenset[str]) -> None:
            captured.append(expected_keys)
            require_json_object_keys(payload, expected_keys)

        with patch(
            "src.application.eventing.outbox.codecs.customers.require_json_object_keys", side_effect=validate
        ):
            self.decode({"customer_id": 7})
            with self.assertRaisesRegex(ValueError, "Missing fields:.*customer_id"):
                self.decode({})
            CustomerCreatedEventPayloadCodec().decode(
                {"customer_id": 8}, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
            )

        self.assertEqual(len(captured), 3)
        self.assertIsInstance(captured[0], frozenset)
        self.assertEqual(captured[0], frozenset({"customer_id"}))
        self.assertTrue(all(keys is captured[0] for keys in captured))

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
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("customer_created", 2)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, {"customer_id": 7})
