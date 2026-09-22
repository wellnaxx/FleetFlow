"""Tests for strict JSON business-timestamp parsing and nullable values."""

import unittest
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from src.shared.json_deserialization import parse_naive_datetime, parse_optional_naive_datetime

PARSERS: tuple[Callable[[object, str], datetime | None], ...] = (
    parse_naive_datetime,
    parse_optional_naive_datetime,
)


class JsonDeserializationShould(unittest.TestCase):
    def test_parses_existing_iso_forms_without_changing_precision_or_business_time(self) -> None:
        expected = datetime(2030, 1, 2, 3, 4, 5, 123456)
        cases = (
            ("2030-01-02T03:04:05.123456", expected),
            ("2030-01-02 03:04:05.123456", expected),
            ("2030-01-02T03:04:05,123456", expected),
            ("20300102T030405.123456", expected),
            ("2030-01-02T03:04:05.123456789", expected),
            ("2030-01-02T03:04:05.1", datetime(2030, 1, 2, 3, 4, 5, 100000)),
            ("2030-01-02T03:04:05", datetime(2030, 1, 2, 3, 4, 5)),
            ("2030-01-02T03:04", datetime(2030, 1, 2, 3, 4)),
            ("2030-01-02", datetime(2030, 1, 2)),
            ("2028-02-29T12:00:00", datetime(2028, 2, 29, 12)),
            (datetime.min.isoformat(), datetime.min),
            (datetime.max.isoformat(), datetime.max),
        )
        for parser in PARSERS:
            for text, expected in cases:
                with self.subTest(parser=parser.__name__, text=text):
                    parsed = parser(text, "departure_time")
                    self.assertEqual(parsed, expected)
                    self.assertIsInstance(parsed, datetime)
                    assert parsed is not None
                    self.assertIsNone(parsed.tzinfo)

    def test_optional_parser_accepts_null_but_required_parser_rejects_it(self) -> None:
        self.assertIsNone(parse_optional_naive_datetime(None, "departure_time"))
        with self.assertRaisesRegex(TypeError, "departure_time: expected str, got NoneType"):
            parse_naive_datetime(None, "departure_time")

    def test_rejects_non_string_values_without_coercion(self) -> None:
        values: tuple[object, ...] = (
            True,
            False,
            0,
            20300102,
            1.5,
            b"2030-01-02T03:04:05",
            [],
            {},
            ("2030-01-02T03:04:05",),
            datetime(2030, 1, 2),
            datetime(2030, 1, 2, tzinfo=UTC),
            uuid4(),
        )
        for parser in PARSERS:
            for value in values:
                with (
                    self.subTest(parser=parser.__name__, value=value),
                    self.assertRaisesRegex(TypeError, "expected_arrival: expected str"),
                ):
                    parser(value, "expected_arrival")

    def test_invalid_text_raises_field_specific_error_with_original_parse_cause(self) -> None:
        values = (
            "",
            "   ",
            "null",
            "not-a-datetime",
            "03:04:05",
            "2030-13-02T03:04:05",
            "2030-02-29T03:04:05",
            "2030-01-02T24:00:00",
            "2030-01-02T03:04:60",
            "0000-01-01",
            "10000-01-01",
            "2030-01-02T03:04:05garbage",
            " 2030-01-02T03:04:05",
            "2030-01-02T03:04:05 ",
        )
        for parser in PARSERS:
            for value in values:
                with self.subTest(parser=parser.__name__, value=value):
                    with self.assertRaises(ValueError) as raised:
                        parser(value, "scheduled_delivery_time")
                    self.assertEqual(
                        str(raised.exception), "scheduled_delivery_time: expected ISO-formatted datetime."
                    )
                    self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_rejects_all_aware_business_timestamps_without_dropping_or_converting_offsets(self) -> None:
        for parser in PARSERS:
            for offset in ("Z", "+00:00", "-00:00", "+10:00", "-04:00", "+05:30"):
                with self.subTest(parser=parser.__name__, offset=offset):
                    with self.assertRaises(ValueError) as raised:
                        parser(f"2030-01-02T03:04:05.123456{offset}", "previous_busy_until")
                    self.assertEqual(str(raised.exception), "previous_busy_until must be timezone-naive.")
                    self.assertIsNone(raised.exception.__cause__)


if __name__ == "__main__":
    unittest.main()
