"""Contracts for flat outbox world-state count serialization and decoding."""

import json
import unittest
from typing import cast

from src.application.eventing.outbox.codecs.entity_counts import decode_entity_counts, encode_entity_counts
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.shared.json_types import JSONObject, JSONValue

PREFIXES = ("", "previous_", "new_")
FIELDS = ("customer_count", "package_count", "route_count", "truck_count")


class EntityCountsCodecHelpersShould(unittest.TestCase):
    def test_encodes_exact_flat_keys_and_decodes_each_field_to_its_own_attribute(self) -> None:
        counts = WorldStateEntityCounts(customers=1, packages=2, routes=3, trucks=4)
        for prefix in PREFIXES:
            with self.subTest(prefix=prefix):
                expected: JSONObject = {
                    f"{prefix}customer_count": 1,
                    f"{prefix}package_count": 2,
                    f"{prefix}route_count": 3,
                    f"{prefix}truck_count": 4,
                }
                encoded = encode_entity_counts(counts, prefix=prefix)
                self.assertEqual(encoded, expected)
                for value in encoded.values():
                    self.assertIs(type(value), int)
                payload = cast(JSONObject, json.loads(json.dumps(encoded)))
                decoded = decode_entity_counts(payload, prefix=prefix)
                self.assertIs(type(decoded), WorldStateEntityCounts)
                self.assertEqual(decoded, counts)

    def test_default_prefix_is_the_unprefixed_export_contract(self) -> None:
        counts = WorldStateEntityCounts(customers=1, packages=2, routes=3, trucks=4)
        self.assertEqual(encode_entity_counts(counts), encode_entity_counts(counts, prefix=""))
        self.assertEqual(decode_entity_counts(encode_entity_counts(counts)), counts)

    def test_accepts_zero_and_large_values_for_each_count(self) -> None:
        for prefix in PREFIXES:
            for field in FIELDS:
                for value in (0, 1, 2**63, 10**100):
                    with self.subTest(prefix=prefix, field=field, value=value):
                        payload: JSONObject = {f"{prefix}{name}": 0 for name in FIELDS}
                        payload[f"{prefix}{field}"] = value
                        decoded = decode_entity_counts(payload, prefix=prefix)
                        self.assertEqual(encode_entity_counts(decoded, prefix=prefix), payload)

    def test_rejects_non_integer_values_using_the_full_wire_field_name(self) -> None:
        values: tuple[JSONValue, ...] = (
            None, True, False, "1", "", 1.0, [], {}, float("nan"), float("inf"),
        )
        for prefix in PREFIXES:
            for field in FIELDS:
                for value in values:
                    key = f"{prefix}{field}"
                    with self.subTest(key=key, value=value):
                        payload: JSONObject = {f"{prefix}{name}": 0 for name in FIELDS}
                        payload[key] = value
                        with self.assertRaisesRegex(TypeError, f"^{key}: expected int"):
                            decode_entity_counts(payload, prefix=prefix)

    def test_rejects_negative_values_using_the_full_wire_field_name(self) -> None:
        for prefix in PREFIXES:
            for field in FIELDS:
                for value in (-1, -(2**63)):
                    key = f"{prefix}{field}"
                    with self.subTest(key=key, value=value):
                        payload: JSONObject = {f"{prefix}{name}": 0 for name in FIELDS}
                        payload[key] = value
                        with self.assertRaisesRegex(ValueError, f"^{key} must be a non-negative integer"):
                            decode_entity_counts(payload, prefix=prefix)

    def test_does_not_default_missing_counts_to_zero_or_read_a_different_prefix(self) -> None:
        counts = WorldStateEntityCounts(customers=1, packages=2, routes=3, trucks=4)
        for prefix in PREFIXES:
            for field in FIELDS:
                key = f"{prefix}{field}"
                with self.subTest(key=key):
                    payload: JSONObject = {
                        **encode_entity_counts(counts),
                        **encode_entity_counts(counts, prefix="previous_"),
                        **encode_entity_counts(counts, prefix="new_"),
                    }
                    del payload[key]
                    with self.assertRaises(KeyError) as raised:
                        decode_entity_counts(payload, prefix=prefix)
                    self.assertEqual(raised.exception.args, (key,))

    def test_reads_groups_independently_without_comparing_before_and_after_counts(self) -> None:
        previous = WorldStateEntityCounts(customers=8, packages=2, routes=3, trucks=0)
        new = WorldStateEntityCounts(customers=1, packages=7, routes=3, trucks=0)
        payload: JSONObject = {
            "snapshot_path": "snapshot.json",
            "schema_version": 1,
            **encode_entity_counts(previous, prefix="previous_"),
            **encode_entity_counts(new, prefix="new_"),
        }
        self.assertEqual(decode_entity_counts(payload, prefix="previous_"), previous)
        self.assertEqual(decode_entity_counts(payload, prefix="new_"), new)
        payload["previous_customer_count"] = -1
        self.assertEqual(decode_entity_counts(payload, prefix="new_"), new)

    def test_results_are_fresh_and_do_not_mutate_or_retain_input_payloads(self) -> None:
        counts = WorldStateEntityCounts(customers=1, packages=2, routes=3, trucks=4)
        for prefix in PREFIXES:
            with self.subTest(prefix=prefix):
                first = encode_entity_counts(counts, prefix=prefix)
                second = encode_entity_counts(counts, prefix=prefix)
                self.assertIsNot(first, second)
                decoded = decode_entity_counts(first, prefix=prefix)
                self.assertEqual(first, second)
                self.assertIsNot(decoded, counts)
                self.assertIsNot(decoded, decode_entity_counts(first, prefix=prefix))
                first[f"{prefix}customer_count"] = 99
                self.assertEqual(decoded, counts)
                self.assertEqual(encode_entity_counts(counts, prefix=prefix), second)


if __name__ == "__main__":
    unittest.main()
