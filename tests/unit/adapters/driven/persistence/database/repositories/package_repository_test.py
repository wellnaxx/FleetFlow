import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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

    @patch(f"{MODULE}.load_world_graph")
    def test_get_by_id_returns_none_when_package_is_missing(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        load_world_graph_mock.return_value = SimpleNamespace(packages={})

        package = self.repo.get_by_id(11)

        self.assertIsNone(package)
        load_world_graph_mock.assert_called_once_with()

    @patch(f"{MODULE}.load_world_graph")
    def test_get_by_id_returns_hydrated_package(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        expected = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 11)
        load_world_graph_mock.return_value = SimpleNamespace(packages={11: expected})

        package = self.repo.get_by_id(11)

        self.assertIs(package, expected)
        load_world_graph_mock.assert_called_once_with()

    @patch(f"{MODULE}.load_world_graph")
    def test_get_by_id_propagates_graph_loader_errors(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        load_world_graph_mock.side_effect = ValueError("Package 11 references missing route 21.")

        with self.assertRaises(ValueError) as ctx:
            self.repo.get_by_id(11)

        self.assertIn("Package 11 references missing route 21.", str(ctx.exception))

    @patch(f"{MODULE}.load_world_graph")
    def test_list_all_returns_hydrated_packages_ordered_by_id(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        packages = [
            DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 11),
            DeliveryPackage(LocationCode("MEL"), LocationCode("SYD"), 10.0, self.customer, 12),
        ]
        load_world_graph_mock.return_value = SimpleNamespace(packages={12: packages[1], 11: packages[0]})

        result = self.repo.list_all()

        self.assertEqual(result, packages)
        load_world_graph_mock.assert_called_once_with()

    @patch(f"{MODULE}.load_world_graph")
    def test_list_unassigned_returns_hydrated_unassigned_packages_ordered_by_id(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        assigned = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 10)
        assigned.route = SimpleNamespace(route_id=21)  # type: ignore[assignment]

        unassigned_1 = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 11)
        unassigned_2 = DeliveryPackage(LocationCode("MEL"), LocationCode("SYD"), 10.0, self.customer, 12)

        load_world_graph_mock.return_value = SimpleNamespace(
            packages={12: unassigned_2, 10: assigned, 11: unassigned_1}
        )

        result = self.repo.list_unassigned()

        self.assertEqual(result, [unassigned_1, unassigned_2])
        load_world_graph_mock.assert_called_once_with()

    @patch(f"{MODULE}.load_world_graph")
    def test_list_by_route_returns_hydrated_route_packages(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        package_1 = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 11)
        package_2 = DeliveryPackage(LocationCode("MEL"), LocationCode("SYD"), 10.0, self.customer, 12)
        route_packages = [package_2, package_1]
        route = SimpleNamespace(packages=route_packages)

        load_world_graph_mock.return_value = SimpleNamespace(routes={21: route})

        result = self.repo.list_by_route(21)

        self.assertEqual(result, [package_1, package_2])
        self.assertIsNot(result, route_packages)
        load_world_graph_mock.assert_called_once_with()

    @patch(f"{MODULE}.load_world_graph")
    def test_list_by_route_returns_empty_list_when_route_is_missing(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        load_world_graph_mock.return_value = SimpleNamespace(routes={})

        result = self.repo.list_by_route(21)

        self.assertEqual(result, [])
        load_world_graph_mock.assert_called_once_with()

    @patch(f"{MODULE}.execute_write")
    def test_update_state_writes_mutable_package_state(self, execute_write_mock: MagicMock) -> None:
        package = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 11)
        package.status = ItemStatus.IN_PROGRESS
        package.current_location = LocationCode("ADL")
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
        package = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 11)

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
