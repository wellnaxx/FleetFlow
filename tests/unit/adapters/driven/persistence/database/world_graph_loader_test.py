import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

from src.adapters.driven.persistence.database.graph_loaders.world_graph_loader import load_world_graph
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus

MODULE = "src.adapters.driven.persistence.database.graph_loaders.world_graph_loader"


class WorldGraphLoaderShould(unittest.TestCase):
    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_world_graph_maps_and_links_customers_routes_packages_and_trucks(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        expected_arrival = datetime(2026, 5, 7, 12, 30)

        fetch_all_tx_mock.side_effect = [
            [self._customer_row(7)],
            [
                self._route_row(21, 0, "SYD", truck_vehicle_id=1001),
                self._route_row(21, 1, "MEL", truck_vehicle_id=1001),
            ],
            [self._package_row(11, customer_id=7, route_id=21, expected_arrival=expected_arrival)],
            [self._truck_row(1001)],
        ]

        graph = load_world_graph()

        customer = graph.customers[7]
        route = graph.routes[21]
        truck = graph.trucks[1001]
        package = graph.packages[11]

        self.assertIs(package.customer, customer)
        self.assertEqual(customer.delivery_packages, (package,))

        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)

        self.assertEqual(route.packages, [package])
        self.assertIs(package.route, route)

        self.assertEqual(package.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(package.current_location, "SYD")
        self.assertEqual(package.expected_arrival, expected_arrival)

        fetch_all_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.customers.list_all),
                call(cursor, QUERIES.routes.list_all),
                call(cursor, QUERIES.packages.list_all),
                call(cursor, QUERIES.trucks.list_all),
            ]
        )
        self.assertEqual(fetch_all_tx_mock.call_count, 4)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_world_graph_keeps_unassigned_edges_empty(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)

        fetch_all_tx_mock.side_effect = [
            [self._customer_row(7)],
            [
                self._route_row(21, 0, "SYD"),
                self._route_row(21, 1, "MEL"),
            ],
            [self._package_row(11, customer_id=7, route_id=None)],
            [self._truck_row(1001)],
        ]

        graph = load_world_graph()

        self.assertIsNone(graph.routes[21].truck)
        self.assertIsNone(graph.trucks[1001].route)

        self.assertEqual(graph.routes[21].packages, [])
        self.assertIsNone(graph.packages[11].route)

        self.assertIs(graph.packages[11].customer, graph.customers[7])
        self.assertEqual(graph.customers[7].delivery_packages, (graph.packages[11],))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_world_graph_raises_when_route_references_missing_truck(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)

        fetch_all_tx_mock.side_effect = [
            [],
            [
                self._route_row(21, 0, "SYD", truck_vehicle_id=999),
                self._route_row(21, 1, "MEL", truck_vehicle_id=999),
            ],
            [],
            [],
        ]

        with self.assertRaises(ValueError) as ctx:
            load_world_graph()

        self.assertIn("Route 21 references missing truck 999.", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_world_graph_raises_when_package_references_missing_customer(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)

        fetch_all_tx_mock.side_effect = [
            [],
            [],
            [self._package_row(11, customer_id=7, route_id=None)],
            [],
        ]

        with self.assertRaises(ValueError) as ctx:
            load_world_graph()

        self.assertIn("Package 11 references missing customer 7.", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_world_graph_raises_when_package_references_missing_route(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)

        fetch_all_tx_mock.side_effect = [
            [self._customer_row(7)],
            [],
            [self._package_row(11, customer_id=7, route_id=21)],
            [],
        ]

        with self.assertRaises(ValueError) as ctx:
            load_world_graph()

        self.assertIn("Package 11 references missing route 21.", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_world_graph_rejects_invalid_foreign_key_types(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)

        row = self._route_row(21, 0, "SYD")
        row["route_id"] = "21"

        fetch_all_tx_mock.side_effect = [
            [],
            [row],
            [],
            [],
        ]

        with self.assertRaises(TypeError) as ctx:
            load_world_graph()

        self.assertIn("route_id: expected int", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_world_graph_rejects_bool_ids(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)

        row = self._route_row(21, 0, "SYD")
        row["route_id"] = True

        fetch_all_tx_mock.side_effect = [
            [],
            [row],
            [],
            [],
        ]

        with self.assertRaises(TypeError) as ctx:
            load_world_graph()

        self.assertIn("route_id: expected int", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_world_graph_rejects_conflicting_route_truck_ids(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)

        fetch_all_tx_mock.side_effect = [
            [],
            [
                self._route_row(21, 0, "SYD", truck_vehicle_id=1001),
                self._route_row(21, 1, "MEL", truck_vehicle_id=1002),
            ],
            [],
            [self._truck_row(1001), self._truck_row(1002)],
        ]

        with self.assertRaises(ValueError) as ctx:
            load_world_graph()

        self.assertIn("Route 21 has inconsistent truck_vehicle_id values", str(ctx.exception))

    def _transaction_cursor(self, transaction_cursor_mock: MagicMock) -> MagicMock:
        cursor = MagicMock()
        transaction_cursor_mock.return_value.__enter__.return_value = cursor
        return cursor

    def _customer_row(self, customer_id: int) -> dict[str, object]:
        return {
            "customer_id": customer_id,
            "name": "Alice",
            "email": "alice@example.com",
            "phone": "0412345678",
        }

    def _route_row(
        self,
        route_id: int,
        stop_order: int,
        location_code: str,
        truck_vehicle_id: int | None = None,
    ) -> dict[str, object]:
        return {
            "route_id": route_id,
            "departure_time": None,
            "status": RouteStatus.PLANNED.value,
            "truck_vehicle_id": truck_vehicle_id,
            "stop_order": stop_order,
            "location_code": location_code,
        }

    def _truck_row(self, vehicle_id: int) -> dict[str, object]:
        return {
            "vehicle_id": vehicle_id,
            "name": TruckModel.SCANIA.value,
            "capacity": 42000,
            "max_range": 8000,
            "status": TruckStatus.ON_THE_WAY.value,
            "current_location": "SYD",
            "busy_from": None,
            "busy_until": None,
            "in_transit_to": "MEL",
        }

    def _package_row(
        self,
        package_id: int,
        *,
        customer_id: int,
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
            "customer_id": customer_id,
            "route_id": route_id,
        }
