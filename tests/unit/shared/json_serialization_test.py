"""Tests for layer-neutral JSON serialization helpers."""

import unittest
from datetime import UTC, datetime
from uuid import UUID

from src.shared.json_serialization import optional_id, optional_isoformat, optional_str


class JsonSerializationShould(unittest.TestCase):
    def test_optional_str_preserves_none_and_stringifies_present_values(self) -> None:
        self.assertIsNone(optional_str(None))
        self.assertEqual(optional_str(42), "42")

    def test_optional_id_preserves_none_and_stringifies_identifiers(self) -> None:
        identifier = UUID("12345678-1234-5678-1234-567812345678")

        self.assertIsNone(optional_id(None))
        self.assertEqual(optional_id(identifier), str(identifier))

    def test_optional_isoformat_preserves_none_and_datetime_timezone_shape(self) -> None:
        naive = datetime(2030, 1, 2, 3, 4, 5)
        aware = datetime(2030, 1, 2, 3, 4, 5, tzinfo=UTC)

        self.assertIsNone(optional_isoformat(None))
        self.assertEqual(optional_isoformat(naive), "2030-01-02T03:04:05")
        self.assertEqual(optional_isoformat(aware), "2030-01-02T03:04:05+00:00")


if __name__ == "__main__":
    unittest.main()
