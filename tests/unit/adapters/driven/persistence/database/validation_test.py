"""Tests for database-facing validation helpers."""

import unittest

from src.adapters.driven.persistence.database.validation import require_count


class RequireCountTest(unittest.TestCase):
    """Verify database counts retain repository-specific error messages."""

    def test_accepts_zero_and_positive_integers(self) -> None:
        """Return valid counts unchanged."""
        self.assertEqual(require_count(0, "Audit record count"), 0)
        self.assertEqual(require_count(3, "Audit record count"), 3)

    def test_rejects_non_integer_values_and_booleans(self) -> None:
        """Reject values that PostgreSQL integer counts cannot represent."""
        for value in (True, 1.0, "1", None):
            with self.subTest(value=value), self.assertRaisesRegex(
                TypeError,
                r"^Audit record count must be an integer\.$",
            ):
                require_count(value, "Audit record count")

    def test_rejects_negative_integers(self) -> None:
        """Reject negative values while preserving the database-facing label."""
        with self.assertRaisesRegex(
            ValueError,
            r"^Audit record count must be non-negative\.$",
        ):
            require_count(-1, "Audit record count")


if __name__ == "__main__":
    unittest.main()
