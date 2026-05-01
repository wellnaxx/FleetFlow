from __future__ import annotations

import unittest
from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.mappers import map_customer

if TYPE_CHECKING:
    from src.adapters.driven.persistence.database.executor import RowDict


class DatabaseMappers_Should(unittest.TestCase):
    def test_map_customer_builds_customer_from_valid_row(self) -> None:
        row: RowDict = {
            "customer_id": 7,
            "name": "Alice",
            "email": "alice@example.com",
            "phone": "0412345678",
        }

        customer = map_customer(row)

        self.assertEqual(customer.customer_id, 7)
        self.assertEqual(customer.name, "Alice")
        self.assertEqual(customer.email, "alice@example.com")
        self.assertEqual(customer.phone_number, "0412345678")

    def test_map_customer_raises_key_error_for_missing_required_column(self) -> None:
        row: RowDict = {
            "customer_id": 7,
            "name": "Alice",
            "email": "alice@example.com",
        }

        with self.assertRaises(KeyError):
            map_customer(row)

    def test_map_customer_raises_type_error_for_invalid_column_types(self) -> None:
        cases: list[tuple[str, object]] = [
            ("customer_id", "7"),
            ("name", None),
            ("email", None),
            ("phone", None),
        ]

        for column, value in cases:
            with self.subTest(column=column):
                row: RowDict = {
                    "customer_id": 7,
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone": "0412345678",
                }
                row[column] = value

                with self.assertRaises(TypeError) as ctx:
                    map_customer(row)

                self.assertIn(f"{column}: expected", str(ctx.exception))

    def test_map_customer_raises_value_error_for_invalid_contact_data(self) -> None:
        row: RowDict = {
            "customer_id": 7,
            "name": "Al",
            "email": "alice@example.com",
            "phone": "0412345678",
        }

        with self.assertRaises(ValueError):
            map_customer(row)
