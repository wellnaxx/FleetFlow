import unittest
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from src.shared.validation import (
    require_aware_datetime,
    require_datetime,
    require_enum,
    require_finite_decimal,
    require_finite_positive_decimal,
    require_int,
    require_naive_datetime,
    require_non_empty_str,
    require_non_negative_finite_float,
    require_non_negative_int,
    require_optional_aware_datetime,
    require_optional_datetime,
    require_optional_int,
    require_optional_naive_datetime,
    require_optional_positive_int,
    require_optional_str,
    require_optional_utc_datetime,
    require_optional_uuid,
    require_positive_finite_float,
    require_positive_int,
    require_str,
    require_utc_datetime,
    require_uuid,
)


class SampleValue(StrEnum):
    VALID = "valid"


class OtherValue(StrEnum):
    VALID = "valid"


class SharedValidation_Should(unittest.TestCase):
    def test_enum_helper_requires_member_of_expected_enum(self) -> None:
        self.assertIsNone(require_enum(SampleValue.VALID, "value", SampleValue))

        for value in ("valid", OtherValue.VALID, None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                require_enum(value, "value", SampleValue)

    def test_require_int_accepts_int_and_rejects_bool_and_other_types(self) -> None:
        self.assertEqual(require_int(3, "value"), 3)

        for value in (True, False, 3.0, "3", None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                require_int(value, "value")

    def test_optional_int_accepts_none_and_rejects_bool(self) -> None:
        self.assertIsNone(require_optional_int(None, "value"))
        self.assertEqual(require_optional_int(3, "value"), 3)

        with self.assertRaisesRegex(TypeError, "expected int or None"):
            require_optional_int(True, "value")

    def test_positive_int_rejects_zero_and_negative_values(self) -> None:
        self.assertEqual(require_positive_int(1, "value"), 1)

        for value in (0, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_positive_int(value, "value")

    def test_optional_positive_int_allows_none(self) -> None:
        self.assertIsNone(require_optional_positive_int(None, "value"))
        self.assertEqual(require_optional_positive_int(1, "value"), 1)

    def test_non_negative_int_accepts_zero_and_rejects_negative_values(self) -> None:
        self.assertEqual(require_non_negative_int(0, "value"), 0)

        with self.assertRaises(ValueError):
            require_non_negative_int(-1, "value")

    def test_string_helpers_preserve_or_normalize_according_to_contract(self) -> None:
        self.assertEqual(require_str(" value ", "value"), " value ")
        self.assertEqual(require_non_empty_str(" value ", "value"), "value")
        self.assertEqual(require_optional_str("", "value"), "")
        self.assertIsNone(require_optional_str(None, "value"))

        with self.assertRaises(ValueError):
            require_non_empty_str("   ", "value")

    def test_datetime_helpers_validate_required_and_optional_values(self) -> None:
        value = datetime(2030, 1, 1, 10, 0)

        self.assertIs(require_datetime(value, "value"), value)
        self.assertIs(require_optional_datetime(value, "value"), value)
        self.assertIsNone(require_optional_datetime(None, "value"))

        with self.assertRaises(TypeError):
            require_datetime("2030-01-01", "value")

    def test_naive_datetime_helpers_reject_effective_timezone_offsets(self) -> None:
        value = datetime(2030, 1, 1, 10, 0)

        self.assertIs(require_naive_datetime(value, "value"), value)
        self.assertIs(require_optional_naive_datetime(value, "value"), value)
        self.assertIsNone(require_optional_naive_datetime(None, "value"))

        with self.assertRaisesRegex(ValueError, "value must be timezone-naive"):
            require_naive_datetime(value.replace(tzinfo=UTC), "value")

    def test_aware_datetime_helpers_accept_any_defined_offset(self) -> None:
        value = datetime(2030, 1, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))

        self.assertIs(require_aware_datetime(value, "value"), value)
        self.assertIs(require_optional_aware_datetime(value, "value"), value)
        self.assertIsNone(require_optional_aware_datetime(None, "value"))

        with self.assertRaisesRegex(ValueError, "value must be timezone-aware"):
            require_aware_datetime(value.replace(tzinfo=None), "value")

    def test_utc_datetime_helpers_require_zero_offset(self) -> None:
        value = datetime(2030, 1, 1, 10, 0, tzinfo=UTC)

        self.assertIs(require_utc_datetime(value, "value"), value)
        self.assertIs(require_optional_utc_datetime(value, "value"), value)
        self.assertIsNone(require_optional_utc_datetime(None, "value"))

        with self.assertRaisesRegex(ValueError, "value must be timezone-aware"):
            require_utc_datetime(value.replace(tzinfo=None), "value")

        non_utc = value.replace(tzinfo=timezone(timedelta(hours=2)))
        with self.assertRaisesRegex(ValueError, "value must use UTC"):
            require_utc_datetime(non_utc, "value")

    def test_uuid_helpers_validate_required_and_optional_values(self) -> None:
        value = uuid4()

        self.assertIs(require_uuid(value, "value"), value)
        self.assertIs(require_optional_uuid(value, "value"), value)
        self.assertIsNone(require_optional_uuid(None, "value"))

        with self.assertRaises(TypeError):
            require_uuid(str(value), "value")

    def test_positive_finite_float_normalizes_numeric_values(self) -> None:
        self.assertEqual(require_positive_finite_float(3, "value"), 3.0)
        self.assertEqual(require_positive_finite_float(3.5, "value"), 3.5)

    def test_positive_finite_float_rejects_invalid_numbers_and_types(self) -> None:
        for value in (True, "3", None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                require_positive_finite_float(value, "value")

        for value in (0, -1, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_positive_finite_float(value, "value")

    def test_positive_finite_float_translates_integer_overflow(self) -> None:
        with self.assertRaisesRegex(ValueError, r"^weight must be finite\.$"):
            require_positive_finite_float(10**10_000, "weight")

    def test_non_negative_finite_float_accepts_zero_and_fractional_values(self) -> None:
        self.assertEqual(require_non_negative_finite_float(0, "load"), 0.0)
        self.assertEqual(require_non_negative_finite_float(1.5, "load"), 1.5)

    def test_non_negative_finite_float_rejects_invalid_values(self) -> None:
        for value in (True, "1", None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                require_non_negative_finite_float(value, "load")

        for value in (-1, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_non_negative_finite_float(value, "load")

        with self.assertRaisesRegex(ValueError, r"^load must be finite\.$"):
            require_non_negative_finite_float(10**10_000, "load")

    def test_finite_decimal_preserves_finite_decimal_values(self) -> None:
        value = Decimal("10.250")

        self.assertIs(require_finite_decimal(value, "weight"), value)
        self.assertIs(require_finite_decimal(Decimal("0"), "weight").is_zero(), True)
        self.assertEqual(require_finite_decimal(Decimal("-1"), "weight"), Decimal("-1"))

    def test_finite_decimal_rejects_other_numeric_types_and_non_finite_values(self) -> None:
        for value in (1, 1.0, True, "1", None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                require_finite_decimal(value, "weight")

        for value in (Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "weight must be finite"):
                require_finite_decimal(value, "weight")

    def test_finite_positive_decimal_accepts_positive_values(self) -> None:
        value = Decimal("0.001")

        self.assertIs(require_finite_positive_decimal(value, "weight"), value)

    def test_finite_positive_decimal_rejects_zero_negative_and_non_finite_values(self) -> None:
        for value, message in (
            (Decimal("0"), "positive"),
            (Decimal("-0.001"), "positive"),
            (Decimal("NaN"), "finite"),
            (Decimal("Infinity"), "finite"),
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, message):
                require_finite_positive_decimal(value, "weight")
