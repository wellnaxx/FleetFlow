import unittest

from src.domain.exceptions import DomainValidationError
from src.domain.validation import (
    require_optional_positive_int,
    require_positive_finite_float,
    require_positive_int,
)


class DomainValidation_Should(unittest.TestCase):
    def test_positive_int_translates_type_and_value_errors(self) -> None:
        for value in (True, "1", 0, -1):
            with self.subTest(value=value), self.assertRaises(DomainValidationError) as context:
                require_positive_int(value, "identifier")

            self.assertIsInstance(context.exception.__cause__, TypeError | ValueError)

    def test_optional_positive_int_accepts_none_and_translates_invalid_values(self) -> None:
        self.assertIsNone(require_optional_positive_int(None, "identifier"))

        with self.assertRaises(DomainValidationError):
            require_optional_positive_int(0, "identifier")

    def test_positive_finite_float_normalizes_and_translates_invalid_values(self) -> None:
        self.assertEqual(require_positive_finite_float(5, "weight"), 5.0)

        for value in (True, "5", 0, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(DomainValidationError):
                require_positive_finite_float(value, "weight")
