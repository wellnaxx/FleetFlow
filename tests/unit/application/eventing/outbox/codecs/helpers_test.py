"""Regression checks for shared codec test assertions and JSON mechanics."""

import unittest
from unittest.mock import patch

from src.application.eventing.outbox.codecs.customers import CustomerCreatedEventPayloadCodec
from src.shared.json_types import JSONObject
from tests.unit.application.eventing.outbox.codecs.helpers import (
    assert_invalid_metadata,
    assert_required_keys,
    json_round_trip,
)


class CodecTestHelpersShould(unittest.TestCase):
    def test_json_round_trip_preserves_values_and_copies_nested_containers(self) -> None:
        payload: JSONObject = {"items": [{"value": None}], "count": 2}
        restored = json_round_trip(payload)
        self.assertEqual(restored, payload)
        self.assertIsNot(restored, payload)
        self.assertIsNot(restored["items"], payload["items"])

    def test_json_round_trip_rejects_non_finite_numbers(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                json_round_trip({"value": value})

    def test_required_keys_checks_null_keys_and_empty_payload_without_mutating_fixture(self) -> None:
        payload: JSONObject = {"required": [1], "nullable": None}
        attempts: list[JSONObject] = []

        def decode(candidate: JSONObject) -> None:
            attempts.append(candidate.copy())
            missing = payload.keys() - candidate.keys()
            candidate.clear()
            raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")

        assert_required_keys(self, decode, payload)

        self.assertEqual(attempts, [{"nullable": None}, {"required": [1]}, {}])
        self.assertEqual(payload, {"required": [1], "nullable": None})

    def test_required_keys_assertion_detects_a_decoder_that_accepts_missing_fields(self) -> None:
        with self.assertRaises(AssertionError):
            assert_required_keys(unittest.TestCase(), lambda payload: payload, {"required": None})

    def test_metadata_assertion_detects_a_decoder_that_ignores_invalid_metadata(self) -> None:
        codec = CustomerCreatedEventPayloadCodec()
        with patch.object(codec, "decode", return_value=None), self.assertRaises(AssertionError):
            assert_invalid_metadata(unittest.TestCase(), codec, {"customer_id": 7})
