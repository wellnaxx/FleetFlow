import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.package_repository import PostgresPackageRepository
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode

MODULE = "src.adapters.driven.persistence.database.repositories.package_repository"


class PostgresPackageRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = PostgresPackageRepository()
        self.customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

    @patch(f"{MODULE}.execute_insert", return_value=42)
    def test_create_inserts_package_and_returns_package(self, execute_insert_mock: MagicMock) -> None:
        package = self.repo.create(
            start_location=LocationCode("SYD"),
            end_location=LocationCode("MEL"),
            weight=12.5,
            customer=self.customer,
        )

        execute_insert_mock.assert_called_once_with(
            QUERIES.packages.add,
            ("SYD", "MEL", 12.5, 7),
        )
        self.assertEqual(package.package_id, 42)
        self.assertEqual(package.start_location, "SYD")
        self.assertEqual(package.end_location, "MEL")
        self.assertEqual(package.weight, 12.5)
        self.assertIs(package.customer, self.customer)

    @patch(f"{MODULE}.execute_write")
    def test_remove_deletes_package_by_id(self, execute_write_mock: MagicMock) -> None:
        self.repo.remove(11)

        execute_write_mock.assert_called_once_with(QUERIES.packages.remove, (11,))

    @patch(f"{MODULE}.fetch_one", return_value=None)
    @patch(f"{MODULE}.map_package")
    @patch(f"{MODULE}.map_customer")
    def test_get_by_id_returns_none_when_package_is_missing(
        self,
        map_customer_mock: MagicMock,
        map_package_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        package = self.repo.get_by_id(11)

        self.assertIsNone(package)
        fetch_one_mock.assert_called_once_with(QUERIES.packages.get_by_id, (11,))
        map_customer_mock.assert_not_called()
        map_package_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_one")
    @patch(f"{MODULE}.map_package")
    @patch(f"{MODULE}.map_customer")
    def test_get_by_id_fetches_customer_and_maps_package(
        self,
        map_customer_mock: MagicMock,
        map_package_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        package_row = {
            "package_id": 11,
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": object(),
            "status": "To Do",
            "current_location": "SYD",
            "expected_arrival": None,
            "customer_id": 7,
            "route_id": None,
        }
        customer_row = {"customer_id": 7, "name": "Alice", "email": "", "phone": ""}
        expected = DeliveryPackage("SYD", "MEL", 12.5, self.customer, 11)
        fetch_one_mock.side_effect = [package_row, customer_row]
        map_customer_mock.return_value = self.customer
        map_package_mock.return_value = expected

        package = self.repo.get_by_id(11)

        self.assertIs(package, expected)
        fetch_one_mock.assert_has_calls(
            [
                call(QUERIES.packages.get_by_id, (11,)),
                call(QUERIES.customers.get_by_id, (7,)),
            ]
        )
        map_customer_mock.assert_called_once_with(customer_row)
        map_package_mock.assert_called_once_with(package_row, self.customer)

    @patch(f"{MODULE}.fetch_one")
    def test_get_by_id_raises_when_package_references_missing_customer(
        self,
        fetch_one_mock: MagicMock,
    ) -> None:
        package_row = {
            "package_id": 11,
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": object(),
            "status": "To Do",
            "current_location": "SYD",
            "expected_arrival": None,
            "customer_id": 7,
            "route_id": None,
        }
        fetch_one_mock.side_effect = [package_row, None]

        with self.assertRaises(ValueError) as ctx:
            self.repo.get_by_id(11)

        self.assertIn("Package 11 references missing customer 7.", str(ctx.exception))

    @patch(f"{MODULE}.fetch_one")
    def test_get_by_id_rejects_invalid_package_customer_id(self, fetch_one_mock: MagicMock) -> None:
        fetch_one_mock.return_value = {
            "package_id": 11,
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": object(),
            "status": "To Do",
            "current_location": "SYD",
            "expected_arrival": None,
            "customer_id": "7",
            "route_id": None,
        }

        with self.assertRaises(TypeError) as ctx:
            self.repo.get_by_id(11)

        self.assertIn("customer_id: expected int", str(ctx.exception))

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_package")
    @patch(f"{MODULE}.map_customer")
    def test_list_all_maps_joined_package_rows(
        self,
        map_customer_mock: MagicMock,
        map_package_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        rows = [
            self._joined_package_row(11, "Alice"),
            self._joined_package_row(12, "Bob"),
        ]
        packages = [
            DeliveryPackage("SYD", "MEL", 12.5, self.customer, 11),
            DeliveryPackage("MEL", "SYD", 10.0, self.customer, 12),
        ]
        fetch_all_mock.return_value = rows
        map_customer_mock.return_value = self.customer
        map_package_mock.side_effect = packages

        result = self.repo.list_all()

        self.assertEqual(result, packages)
        fetch_all_mock.assert_called_once_with(QUERIES.packages.list_all)
        self.assertEqual(map_customer_mock.call_args_list[0].args[0]["name"], "Alice")
        self.assertEqual(map_customer_mock.call_args_list[1].args[0]["name"], "Bob")
        self.assertEqual(
            [map_call.args for map_call in map_package_mock.call_args_list],
            [(rows[0], self.customer), (rows[1], self.customer)],
        )

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_package")
    @patch(f"{MODULE}.map_customer")
    def test_list_unassigned_maps_joined_package_rows(
        self,
        map_customer_mock: MagicMock,
        map_package_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        row = self._joined_package_row(11, "Alice")
        expected = DeliveryPackage("SYD", "MEL", 12.5, self.customer, 11)
        fetch_all_mock.return_value = [row]
        map_customer_mock.return_value = self.customer
        map_package_mock.return_value = expected

        result = self.repo.list_unassigned()

        self.assertEqual(result, [expected])
        fetch_all_mock.assert_called_once_with(QUERIES.packages.list_unassigned)
        map_customer_mock.assert_called_once_with(
            {
                "customer_id": 7,
                "name": "Alice",
                "email": "alice@example.com",
                "phone": "0412345678",
            }
        )
        map_package_mock.assert_called_once_with(row, self.customer)

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_package")
    @patch(f"{MODULE}.map_customer")
    def test_list_by_route_maps_joined_package_rows(
        self,
        map_customer_mock: MagicMock,
        map_package_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        row = self._joined_package_row(11, "Alice")
        expected = DeliveryPackage("SYD", "MEL", 12.5, self.customer, 11)
        fetch_all_mock.return_value = [row]
        map_customer_mock.return_value = self.customer
        map_package_mock.return_value = expected

        result = self.repo.list_by_route(21)

        self.assertEqual(result, [expected])
        fetch_all_mock.assert_called_once_with(QUERIES.packages.list_by_route, (21,))
        map_package_mock.assert_called_once_with(row, self.customer)

    @patch(f"{MODULE}.execute_write")
    def test_update_state_writes_mutable_package_state(self, execute_write_mock: MagicMock) -> None:
        package = DeliveryPackage("SYD", "MEL", 12.5, self.customer, 11)
        package.status = ItemStatus.IN_PROGRESS
        package.current_location = "ADL"
        package.expected_arrival = datetime(2026, 5, 1, 12, 30)
        package.route = SimpleNamespace(route_id=21)  # type: ignore[assignment]

        self.repo.update_state(package)

        execute_write_mock.assert_called_once_with(
            QUERIES.packages.update_state,
            (
                ItemStatus.IN_PROGRESS.value,
                "ADL",
                datetime(2026, 5, 1, 12, 30),
                21,
                11,
            ),
        )

    @patch(f"{MODULE}.execute_write")
    def test_update_state_writes_null_route_when_package_is_unassigned(
        self,
        execute_write_mock: MagicMock,
    ) -> None:
        package = DeliveryPackage("SYD", "MEL", 12.5, self.customer, 11)

        self.repo.update_state(package)

        execute_write_mock.assert_called_once_with(
            QUERIES.packages.update_state,
            (
                ItemStatus.TODO.value,
                "SYD",
                None,
                None,
                11,
            ),
        )

    def _joined_package_row(self, package_id: int, customer_name: str) -> dict[str, object]:
        return {
            "package_id": package_id,
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": object(),
            "status": "To Do",
            "current_location": "SYD",
            "expected_arrival": None,
            "customer_id": 7,
            "route_id": None,
            "customer_name": customer_name,
            "customer_email": "alice@example.com",
            "customer_phone": "0412345678",
        }
