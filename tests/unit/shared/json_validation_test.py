"""Tests for shared JSON-object validation."""

import unittest
from datetime import datetime
from typing import Any, cast

from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object, require_json_object_keys


class JsonValidationShould(unittest.TestCase):
    def test_exact_keys_accept_null_values_and_empty_contracts_without_mutation(self) -> None:
        value: JSONObject = {"id": None, "items": []}
        expected = frozenset({"items", "id"})
        self.assertIsNone(require_json_object_keys(value, expected))
        self.assertEqual(value, {"id": None, "items": []})
        self.assertEqual(expected, frozenset({"id", "items"}))
        self.assertIsNone(require_json_object_keys({}, frozenset()))

    def test_exact_keys_reports_sorted_missing_fields(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            require_json_object_keys({}, frozenset({"z", "a"}))
        self.assertEqual(str(ctx.exception), "Missing fields: ['a', 'z']")

    def test_exact_keys_reports_sorted_unexpected_fields_before_missing_fields(self) -> None:
        for expected in (frozenset[str](), frozenset({"missing"})):
            with self.subTest(expected=expected):
                with self.assertRaises(ValueError) as ctx:
                    require_json_object_keys({"z": None, "a": None}, expected)
                self.assertEqual(str(ctx.exception), "Unexpected fields: ['a', 'z']")

    def test_accepts_nested_json_and_returns_new_top_level_dict(self) -> None:
        value: JSONObject = {
            "id": 7,
            "active": True,
            "items": [None, 1.5, {"name": "package"}],
        }

        result = require_json_object(value, "payload")

        self.assertEqual(result, value)
        self.assertIsNot(result, value)

    def test_rejects_non_dict_top_level_value(self) -> None:
        with self.assertRaisesRegex(TypeError, "payload: expected JSON object"):
            require_json_object([], "payload")

    def test_rejects_non_string_object_keys(self) -> None:
        value = cast(JSONObject, {1: "invalid"})

        with self.assertRaisesRegex(TypeError, "payload: expected JSON object keys as strings"):
            require_json_object(value, "payload")

    def test_rejects_non_json_nested_values(self) -> None:
        for value in (datetime(2030, 1, 1), (1, 2), b"bytes", object()):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "payload.value"):
                require_json_object({"value": cast(Any, value)}, "payload")

    def test_rejects_non_finite_numbers_at_any_depth(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "expected finite JSON number"):
                require_json_object({"nested": [value]}, "payload")
