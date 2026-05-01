from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.mappers import map_customer, map_package
from src.domain.entities.customer import Customer
from src.domain.enums.item_status import ItemStatus
from src.domain.value_objects.contact_info import ContactInfo

if TYPE_CHECKING:
    from src.adapters.driven.persistence.database.executor import RowDict


class DatabaseMappers_Should(unittest.TestCase):
    def _valid_package_row(self) -> RowDict:
        return {
            "package_id": 11,
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": Decimal("12.50"),
            "status": "To Do",
            "current_location": "SYD",
            "expected_arrival": None,
            "customer_id": 7,
            "route_id": None,
        }

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

    def test_map_package_builds_package_from_valid_row(self) -> None:
        row = self._valid_package_row()
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

        package = map_package(row, customer)

        self.assertEqual(package.package_id, 11)
        self.assertEqual(package.start_location, "SYD")
        self.assertEqual(package.end_location, "MEL")
        self.assertEqual(package.weight, 12.5)
        self.assertIs(package.customer, customer)
        self.assertEqual(package.status, ItemStatus.TODO)
        self.assertEqual(package.current_location, "SYD")
        self.assertIsNone(package.expected_arrival)
        self.assertIsNone(package.route)

    def test_map_package_applies_nullable_route_state_fields(self) -> None:
        row = self._valid_package_row()
        expected_arrival = datetime(2026, 5, 1, 12, 30)
        row["status"] = "In Progress"
        row["current_location"] = None
        row["expected_arrival"] = expected_arrival
        row["route_id"] = 99
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

        package = map_package(row, customer)

        self.assertEqual(package.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(package.current_location, "SYD")
        self.assertIs(package.expected_arrival, expected_arrival)
        self.assertIsNone(package.route)

    def test_map_package_raises_key_error_for_missing_required_column(self) -> None:
        row = self._valid_package_row()
        del row["route_id"]
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

        with self.assertRaises(KeyError):
            map_package(row, customer)

    def test_map_package_raises_type_error_for_invalid_column_types(self) -> None:
        cases: list[tuple[str, object]] = [
            ("package_id", "11"),
            ("start_location", None),
            ("end_location", None),
            ("weight", 12.5),
            ("status", None),
            ("current_location", 1),
            ("expected_arrival", "2026-05-01"),
            ("customer_id", "7"),
            ("route_id", "99"),
        ]
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

        for column, value in cases:
            with self.subTest(column=column):
                row = self._valid_package_row()
                row[column] = value

                with self.assertRaises(TypeError) as ctx:
                    map_package(row, customer)

                self.assertIn(f"{column}: expected", str(ctx.exception))

    def test_map_package_raises_value_error_for_invalid_persisted_values(self) -> None:
        row = self._valid_package_row()
        row["status"] = "Unknown"
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

        with self.assertRaises(ValueError):
            map_package(row, customer)
