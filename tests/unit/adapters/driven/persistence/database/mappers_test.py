from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.mappers.customer import map_customer
from src.adapters.driven.persistence.database.mappers.package import map_package
from src.adapters.driven.persistence.database.mappers.route import map_route
from src.adapters.driven.persistence.database.mappers.truck import map_truck
from src.adapters.driven.persistence.database.mappers.user import map_user_record
from src.domain.entities.customer import Customer
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.contact_info import ContactInfo

if TYPE_CHECKING:
    from src.adapters.driven.persistence.database.executor import RowDict


class DatabaseMappers_Should(unittest.TestCase):
    def _valid_user_row(self) -> RowDict:
        return {
            "user_id": 5,
            "username": "Alice",
            "role": "MANAGER",
            "name": "Alice Admin",
            "email": "alice@example.com",
            "phone": "0412345678",
            "password_hash": "pbkdf2_sha256$200000$salt$hash",
            "token_version": 3,
        }

    def _valid_route_rows(self) -> list[RowDict]:
        return [
            {
                "route_id": 21,
                "departure_time": None,
                "status": "PLANNED",
                "truck_vehicle_id": None,
                "stop_order": 0,
                "location_code": "SYD",
            },
            {
                "route_id": 21,
                "departure_time": None,
                "status": "PLANNED",
                "truck_vehicle_id": None,
                "stop_order": 1,
                "location_code": "MEL",
            },
        ]

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

    def _valid_truck_row(self) -> RowDict:
        return {
            "vehicle_id": 1001,
            "name": "Scania",
            "capacity": 42000,
            "max_range": 8000,
            "status": "Available",
            "current_location": "SYD",
            "busy_from": None,
            "busy_until": None,
            "in_transit_to": None,
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
            ("customer_id", True),
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

    def test_map_customer_raises_domain_validation_error_for_invalid_contact_data(self) -> None:
        row: RowDict = {
            "customer_id": 7,
            "name": "Al",
            "email": "alice@example.com",
            "phone": "0412345678",
        }

        with self.assertRaises(DomainValidationError):
            map_customer(row)

    def test_map_user_record_builds_user_record_from_valid_row(self) -> None:
        row = self._valid_user_row()

        user = map_user_record(row)

        self.assertEqual(user.user_id, 5)
        self.assertEqual(user.username, "Alice")
        self.assertEqual(user.role, "MANAGER")
        self.assertEqual(user.name, "Alice Admin")
        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.phone_number, "0412345678")
        self.assertEqual(user.password, "pbkdf2_sha256$200000$salt$hash")
        self.assertEqual(user.token_version, 3)

    def test_map_user_record_raises_key_error_for_missing_required_column(self) -> None:
        row = self._valid_user_row()
        del row["password_hash"]

        with self.assertRaises(KeyError):
            map_user_record(row)

    def test_map_user_record_raises_type_error_for_invalid_column_types(self) -> None:
        cases: list[tuple[str, object]] = [
            ("user_id", "5"),
            ("user_id", True),
            ("username", None),
            ("role", None),
            ("name", None),
            ("email", None),
            ("phone", None),
            ("password_hash", None),
            ("token_version", None),
            ("token_version", True),
        ]

        for column, value in cases:
            with self.subTest(column=column):
                row = self._valid_user_row()
                row[column] = value

                with self.assertRaises(TypeError) as ctx:
                    map_user_record(row)

                self.assertIn(f"{column}: expected", str(ctx.exception))

    def test_map_user_record_raises_value_error_for_invalid_token_version(self) -> None:
        row = self._valid_user_row()
        row["token_version"] = 0

        with self.assertRaises(ValueError) as ctx:
            map_user_record(row)

        self.assertIn("token_version must be positive", str(ctx.exception))

    def test_map_route_builds_route_from_ordered_stop_rows(self) -> None:
        rows = self._valid_route_rows()

        route = map_route(rows)

        self.assertEqual(route.route_id, 21)
        self.assertEqual(route.locations, ["SYD", "MEL"])
        self.assertIsNone(route.departure_time)
        self.assertEqual(route.status, RouteStatus.PLANNED)
        self.assertIsNone(route.truck)

    def test_map_route_applies_departure_and_persisted_status(self) -> None:
        departure_time = datetime(2026, 5, 1, 9, 0)
        rows = self._valid_route_rows()
        for row in rows:
            row["departure_time"] = departure_time
            row["status"] = "IN_PROGRESS"
            row["truck_vehicle_id"] = 1001

        route = map_route(rows)

        self.assertIs(route.departure_time, departure_time)
        self.assertEqual(route.status, RouteStatus.IN_PROGRESS)

    def test_map_route_raises_value_error_for_empty_rows(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            map_route([])

        self.assertIn("Cannot map a route without route rows.", str(ctx.exception))

    def test_map_route_raises_key_error_for_missing_required_column(self) -> None:
        rows = self._valid_route_rows()
        del rows[0]["route_id"]

        with self.assertRaises(KeyError):
            map_route(rows)

    def test_map_route_raises_type_error_for_invalid_route_column_types(self) -> None:
        cases: list[tuple[str, object]] = [
            ("route_id", "21"),
            ("route_id", True),
            ("departure_time", "2026-05-01"),
            ("status", None),
            ("truck_vehicle_id", "1001"),
            ("truck_vehicle_id", True),
        ]

        for column, value in cases:
            with self.subTest(column=column):
                rows = self._valid_route_rows()
                rows[0][column] = value

                with self.assertRaises(TypeError) as ctx:
                    map_route(rows)

                self.assertIn(f"{column}: expected", str(ctx.exception))

    def test_map_route_raises_type_error_for_invalid_stop_column_types(self) -> None:
        cases: list[tuple[str, object]] = [
            ("stop_order", "0"),
            ("stop_order", True),
            ("location_code", None),
        ]

        for column, value in cases:
            with self.subTest(column=column):
                rows = self._valid_route_rows()
                rows[0][column] = value

                with self.assertRaises(TypeError) as ctx:
                    map_route(rows)

                self.assertIn(f"{column}: expected", str(ctx.exception))

    def test_map_route_raises_value_error_for_invalid_persisted_status(self) -> None:
        rows = self._valid_route_rows()
        rows[0]["status"] = "UNKNOWN"

        with self.assertRaises(ValueError):
            map_route(rows)

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
        self.assertIsNone(package.route_id)

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
        self.assertEqual(package.route_id, 99)

    def test_map_package_raises_key_error_for_missing_required_column(self) -> None:
        row = self._valid_package_row()
        del row["route_id"]
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

        with self.assertRaises(KeyError):
            map_package(row, customer)

    def test_map_package_raises_type_error_for_invalid_column_types(self) -> None:
        cases: list[tuple[str, object]] = [
            ("package_id", "11"),
            ("package_id", True),
            ("start_location", None),
            ("end_location", None),
            ("weight", 12.5),
            ("status", None),
            ("current_location", 1),
            ("expected_arrival", "2026-05-01"),
            ("customer_id", "7"),
            ("customer_id", True),
            ("route_id", "99"),
            ("route_id", True),
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

    def test_map_truck_rejects_bool_integer_columns(self) -> None:
        cases = ["vehicle_id", "capacity", "max_range"]

        for column in cases:
            with self.subTest(column=column):
                row = self._valid_truck_row()
                row[column] = True

                with self.assertRaises(TypeError) as ctx:
                    map_truck(row)

                self.assertIn(f"{column}: expected", str(ctx.exception))
