import unittest
from datetime import UTC, datetime

from src.adapters.driving.cli.commands.validation_helpers import (
    parse_departure_from_tail,
    try_parse_datetime,
    try_parse_float,
    try_parse_int,
    validate_params_count,
    validate_params_exact,
)


class ValidateParamsCount_Should(unittest.TestCase):
    def test_allows_when_only_min_and_enough(self):
        validate_params_count(["a", "b"], 2)  # no exception

    def test_raises_when_only_min_and_too_few(self):
        with self.assertRaises(ValueError) as ctx:
            validate_params_count(["a"], 2)
        self.assertIn("at least 2", str(ctx.exception))

    def test_allows_within_min_max_bounds(self):
        validate_params_count(["a", "b", "c"], 2, 4)  # no exception

    def test_raises_when_below_min_with_max(self):
        with self.assertRaises(ValueError) as ctx:
            validate_params_count(["a"], 2, 4)
        self.assertIn("between 2 and 4", str(ctx.exception))
        self.assertIn("received: 1", str(ctx.exception))

    def test_raises_when_above_max(self):
        with self.assertRaises(ValueError) as ctx:
            validate_params_count(["a", "b", "c", "d", "e"], 2, 4)
        self.assertIn("between 2 and 4", str(ctx.exception))
        self.assertIn("received: 5", str(ctx.exception))


class ValidateParamsExact_Should(unittest.TestCase):
    def test_exact_ok(self):
        validate_params_exact(["x", "y"], 2)  # no exception

    def test_exact_too_few_raises(self):
        with self.assertRaises(ValueError) as ctx:
            validate_params_exact(["x"], 2)
        self.assertIn("exactly 2", str(ctx.exception))
        self.assertIn("received: 1", str(ctx.exception))

    def test_exact_too_many_raises(self):
        with self.assertRaises(ValueError) as ctx:
            validate_params_exact(["x", "y", "z"], 2)
        self.assertIn("exactly 2", str(ctx.exception))
        self.assertIn("received: 3", str(ctx.exception))


class TryParseInt_Should(unittest.TestCase):
    def test_parses_positive(self):
        self.assertEqual(try_parse_int("42"), 42)

    def test_parses_negative(self):
        self.assertEqual(try_parse_int("-7"), -7)

    def test_invalid_raises_with_message(self):
        with self.assertRaises(ValueError) as ctx:
            try_parse_int("4.2")
        self.assertIn("Invalid value for value", str(ctx.exception))

    def test_invalid_uses_supplied_field_name(self):
        with self.assertRaises(ValueError) as ctx:
            try_parse_int("4.2", "--limit")
        self.assertIn("Invalid value for --limit", str(ctx.exception))


class TryParseFloat_Should(unittest.TestCase):
    def test_parses_integer_string(self):
        self.assertEqual(try_parse_float("10"), 10.0)

    def test_parses_decimal_string(self):
        self.assertAlmostEqual(try_parse_float("3.1415"), 3.1415)

    def test_invalid_raises_with_message(self):
        with self.assertRaises(ValueError) as ctx:
            try_parse_float("abc")
        self.assertIn("Invalid value for value", str(ctx.exception))

    def test_invalid_uses_supplied_field_name(self):
        with self.assertRaises(ValueError) as ctx:
            try_parse_float("abc", "weight")
        self.assertIn("Invalid value for weight", str(ctx.exception))


class TryParseDatetime_Should(unittest.TestCase):
    def test_parse_naive_and_utc_iso_timestamps(self) -> None:
        self.assertEqual(
            try_parse_datetime("2026-07-06T14:30:00", "--occurred_from"),
            datetime(2026, 7, 6, 14, 30),
        )
        self.assertEqual(
            try_parse_datetime("2026-07-06T14:30:00Z", "--created_from"),
            datetime(2026, 7, 6, 14, 30, tzinfo=UTC),
        )

    def test_reject_invalid_datetime_with_field_context(self) -> None:
        with self.assertRaisesRegex(ValueError, "--created_from must be a datetime"):
            try_parse_datetime("tomorrow", "--created_from")


class ParseDepartureFromTail_Should(unittest.TestCase):
    def test_empty_tokens_returns_none(self):
        tokens, dt = parse_departure_from_tail([])
        self.assertEqual(tokens, [])
        self.assertIsNone(dt)

    def test_two_token_datetime_at_tail(self):
        locs, dt = parse_departure_from_tail(["SYD", "MEL", "2025-10-12", "06:00"])
        self.assertEqual(locs, ["SYD", "MEL"])
        self.assertEqual(dt, datetime(2025, 10, 12, 6, 0))

    def test_single_token_datetime_at_tail(self):
        # Simulates shell-quoted "YYYY-MM-DD HH:MM" becoming a single token
        locs, dt = parse_departure_from_tail(["SYD", "MEL", "2025-10-12 06:00"])
        self.assertEqual(locs, ["SYD", "MEL"])
        self.assertEqual(dt, datetime(2025, 10, 12, 6, 0))

    def test_last_two_not_datetime_leaves_tokens_unchanged(self):
        locs, dt = parse_departure_from_tail(["SYD", "MEL", "soon", "maybe"])
        self.assertEqual(locs, ["SYD", "MEL", "soon", "maybe"])
        self.assertIsNone(dt)

    def test_last_one_not_datetime_leaves_tokens_unchanged(self):
        locs, dt = parse_departure_from_tail(["SYD", "MEL", "tomorrow"])
        self.assertEqual(locs, ["SYD", "MEL", "tomorrow"])
        self.assertIsNone(dt)
