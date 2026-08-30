"""Tests for shared JSON-object validation."""

import unittest
from datetime import datetime
from typing import Any, cast

from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object


class JsonValidationShould(unittest.TestCase):
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
