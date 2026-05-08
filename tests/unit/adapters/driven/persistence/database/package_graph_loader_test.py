import unittest
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.graph_loaders.package_graph_loader import (
    load_package_graph,
    load_package_graphs,
    load_unassigned_package_graphs,
)
from src.adapters.driven.persistence.database.graph_loaders.route_graph_loader import HydratedRouteGraph
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.item_status import ItemStatus
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode

MODULE = "src.adapters.driven.persistence.database.graph_loaders.package_graph_loader"


class PackageGraphLoaderShould(unittest.TestCase):
    def setUp(self) -> None:
        self.customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_package_graph_returns_none_when_package_is_missing(
        self,
        fetch_one_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_one_tx_mock.return_value = None

        graph = load_package_graph(11)

        self.assertIsNone(graph)
        fetch_one_tx_mock.assert_called_once_with(cursor, QUERIES.packages.get_by_id_with_customer, (11,))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_package_graph_maps_unassigned_package_without_route_hydration(
        self,
        fetch_one_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        fetch_one_tx_mock.return_value = self._package_row(11, route_id=None)

        graph = load_package_graph(11)

        self.assertIsNotNone(graph)
        assert graph is not None
        self.assertEqual(graph.package.package_id, 11)
        self.assertIs(graph.customer, graph.package.customer)
        self.assertIsNone(graph.route)
        self.assertIsNone(graph.package.route)
        load_route_graph_tx_mock.assert_not_called()

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_package_graph_returns_route_owned_package_when_assigned(
        self,
        fetch_one_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)
        package = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 11)
        route.restore_package_link(package, refresh_expected_arrival=False)
        route_graph = self._route_graph(route, {11: package})

        fetch_one_tx_mock.return_value = self._package_row(11, route_id=21)
        load_route_graph_tx_mock.return_value = route_graph

        graph = load_package_graph(11)

        self.assertIsNotNone(graph)
        assert graph is not None
        self.assertIs(graph.package, package)
        self.assertIs(graph.customer, package.customer)
        self.assertIs(graph.route, route)
        load_route_graph_tx_mock.assert_called_once_with(cursor, 21)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_package_graphs_reuses_route_graphs_for_packages_on_same_route(
        self,
        fetch_all_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)
        package_1 = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 12.5, self.customer, 11)
        package_2 = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 10.0, self.customer, 12)
        route.restore_package_link(package_2, refresh_expected_arrival=False)
        route.restore_package_link(package_1, refresh_expected_arrival=False)
        route_graph = self._route_graph(route, {12: package_2, 11: package_1})

        fetch_all_tx_mock.return_value = [
            self._package_row(12, route_id=21),
            self._package_row(11, route_id=21),
        ]
        load_route_graph_tx_mock.return_value = route_graph

        graphs = load_package_graphs()

        self.assertEqual([graph.package.package_id for graph in graphs], [11, 12])
        self.assertIs(graphs[0].package, package_1)
        self.assertIs(graphs[1].package, package_2)
        fetch_all_tx_mock.assert_called_once_with(cursor, QUERIES.packages.list_all_with_customers)
        load_route_graph_tx_mock.assert_called_once_with(cursor, 21)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_unassigned_package_graphs_maps_unassigned_packages(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.return_value = [
            self._package_row(12, route_id=None),
            self._package_row(11, route_id=None),
        ]

        graphs = load_unassigned_package_graphs()

        self.assertEqual([graph.package.package_id for graph in graphs], [12, 11])
        self.assertTrue(all(graph.route is None for graph in graphs))
        fetch_all_tx_mock.assert_called_once_with(cursor, QUERIES.packages.list_unassigned)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_package_graph_raises_when_assigned_route_is_missing(
        self,
        fetch_one_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        fetch_one_tx_mock.return_value = self._package_row(11, route_id=21)
        load_route_graph_tx_mock.return_value = None

        with self.assertRaises(ValueError) as ctx:
            load_package_graph(11)

        self.assertIn("Package 11 references missing route 21.", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_package_graph_raises_when_route_graph_omits_assigned_package(
        self,
        fetch_one_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)

        fetch_one_tx_mock.return_value = self._package_row(11, route_id=21)
        load_route_graph_tx_mock.return_value = self._route_graph(route, {})

        with self.assertRaises(ValueError) as ctx:
            load_package_graph(11)

        self.assertIn("Package 11 has route_id=21 in the database", str(ctx.exception))

    def _transaction_cursor(self, transaction_cursor_mock: MagicMock) -> MagicMock:
        cursor = MagicMock()
        transaction_cursor_mock.return_value.__enter__.return_value = cursor
        return cursor

    def _route_graph(
        self,
        route: DeliveryRoute,
        packages: dict[int, DeliveryPackage],
    ) -> HydratedRouteGraph:
        customers = {package.customer.customer_id: package.customer for package in packages.values()}
        return HydratedRouteGraph(
            route=route,
            truck=None,
            packages=MappingProxyType(packages),
            customers=MappingProxyType(customers),
        )

    def _package_row(
        self,
        package_id: int,
        *,
        route_id: int | None,
        expected_arrival: datetime | None = None,
    ) -> dict[str, object]:
        return {
            "package_id": package_id,
            "start_location": "SYD",
            "end_location": "MEL",
            "weight": Decimal("12.50"),
            "status": ItemStatus.IN_PROGRESS.value,
            "current_location": "SYD",
            "expected_arrival": expected_arrival,
            "customer_id": 7,
            "route_id": route_id,
            "customer_name": "Alice",
            "customer_email": "alice@example.com",
            "customer_phone": "0412345678",
        }
