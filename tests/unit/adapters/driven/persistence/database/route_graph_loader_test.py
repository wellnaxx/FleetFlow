import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

from src.adapters.driven.persistence.database.graph_loaders.route_graph_loader import (
    load_route_graph,
    load_route_graph_page,
    load_route_graph_page_with_total,
    load_route_graph_tx,
    load_route_graphs,
)
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode

MODULE = "src.adapters.driven.persistence.database.graph_loaders.route_graph_loader"


class RouteGraphLoaderShould(unittest.TestCase):
    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_one_tx")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graph_maps_and_links_route_aggregate(
        self,
        fetch_all_tx_mock: MagicMock,
        fetch_one_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        expected_arrival = datetime(2026, 5, 7, 12, 30)

        fetch_all_tx_mock.side_effect = [
            [
                self._route_row(21, 1, "MEL", truck_vehicle_id=1001),
                self._route_row(21, 0, "SYD", truck_vehicle_id=1001),
            ],
            [self._joined_package_row(11, customer_id=7, route_id=21, expected_arrival=expected_arrival)],
        ]
        fetch_one_tx_mock.return_value = self._truck_row(1001)

        graph = load_route_graph(21)

        self.assertIsNotNone(graph)
        assert graph is not None

        route = graph.route
        truck = graph.truck
        package = graph.packages[11]
        customer = graph.customers[7]

        self.assertEqual(route.route_id, 21)
        self.assertEqual(route.locations, [LocationCode("SYD"), LocationCode("MEL")])
        self.assertIs(route.truck, truck)
        self.assertIsNotNone(truck)
        assert truck is not None
        self.assertIs(truck.route, route)

        self.assertEqual(route.packages, (package,))
        self.assertIs(package.route, route)
        self.assertEqual(package.route_id, 21)
        self.assertIs(package.customer, customer)
        self.assertEqual(customer.delivery_packages, (package,))
        self.assertEqual(package.expected_arrival, expected_arrival)

        fetch_all_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.routes.get_by_id, (21,)),
                call(cursor, QUERIES.packages.list_by_route, (21,)),
            ]
        )
        fetch_one_tx_mock.assert_called_once_with(cursor, QUERIES.trucks.get_by_route_id, (21,))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_one_tx")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graph_tx_reuses_existing_cursor_without_opening_transaction(
        self,
        fetch_all_tx_mock: MagicMock,
        fetch_one_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = MagicMock()
        fetch_all_tx_mock.side_effect = [
            [
                self._route_row(21, 0, "SYD"),
                self._route_row(21, 1, "MEL"),
            ],
            [],
        ]
        fetch_one_tx_mock.return_value = None

        graph = load_route_graph_tx(cursor, 21)

        self.assertIsNotNone(graph)
        assert graph is not None
        self.assertEqual(graph.route.route_id, 21)
        self.assertIsNone(graph.truck)
        transaction_cursor_mock.assert_not_called()
        fetch_all_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.routes.get_by_id, (21,)),
                call(cursor, QUERIES.packages.list_by_route, (21,)),
            ]
        )
        fetch_one_tx_mock.assert_called_once_with(cursor, QUERIES.trucks.get_by_route_id, (21,))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_one_tx")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graph_returns_none_when_route_is_missing(
        self,
        fetch_all_tx_mock: MagicMock,
        fetch_one_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.side_effect = [[], []]
        fetch_one_tx_mock.return_value = None

        graph = load_route_graph(21)

        self.assertIsNone(graph)
        fetch_all_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.routes.get_by_id, (21,)),
                call(cursor, QUERIES.packages.list_by_route, (21,)),
            ]
        )
        fetch_one_tx_mock.assert_called_once_with(cursor, QUERIES.trucks.get_by_route_id, (21,))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_one_tx")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graph_rejects_package_from_other_route(
        self,
        fetch_all_tx_mock: MagicMock,
        fetch_one_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.side_effect = [
            [
                self._route_row(21, 0, "SYD"),
                self._route_row(21, 1, "MEL"),
            ],
            [self._joined_package_row(11, customer_id=7, route_id=22)],
        ]
        fetch_one_tx_mock.return_value = None

        with self.assertRaises(ValueError) as ctx:
            load_route_graph(21)

        self.assertIn("Package 11 belongs to route 22, but route 21 was requested.", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graphs_maps_many_route_aggregates_without_free_fleet(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.side_effect = [
            [
                self._route_row(22, 0, "ADL"),
                self._route_row(22, 1, "PER"),
                self._route_row(21, 0, "SYD", truck_vehicle_id=1001),
                self._route_row(21, 1, "MEL", truck_vehicle_id=1001),
            ],
            [self._truck_row(1001)],
            [
                self._joined_package_row(12, customer_id=8, route_id=22),
                self._joined_package_row(11, customer_id=7, route_id=21),
            ],
        ]

        graphs = load_route_graphs()

        self.assertEqual([graph.route.route_id for graph in graphs], [21, 22])

        route_21 = graphs[0].route
        route_22 = graphs[1].route

        self.assertIsNotNone(route_21.truck)
        self.assertIsNone(route_22.truck)
        self.assertEqual([package.package_id for package in route_21.packages], [11])
        self.assertEqual([package.package_id for package in route_22.packages], [12])
        self.assertEqual([package.route_id for package in route_21.packages], [21])
        self.assertEqual([package.route_id for package in route_22.packages], [22])

        fetch_all_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.routes.list_all),
                call(cursor, QUERIES.trucks.list_assigned_by_routes, ([21, 22],)),
                call(cursor, QUERIES.packages.list_assigned_by_routes, ([21, 22],)),
            ]
        )
        self.assertEqual(fetch_all_tx_mock.call_count, 3)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graph_page_maps_requested_route_page(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.side_effect = [
            [
                self._route_row(22, 0, "ADL"),
                self._route_row(22, 1, "PER"),
            ],
            [],
            [],
        ]

        graphs = load_route_graph_page(limit=10, offset=20)

        self.assertEqual([graph.route.route_id for graph in graphs], [22])
        fetch_all_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.routes.list_page, (10, 20)),
                call(cursor, QUERIES.trucks.list_assigned_by_routes, ([22],)),
                call(cursor, QUERIES.packages.list_assigned_by_routes, ([22],)),
            ]
        )

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graph_page_with_total_maps_page_and_total(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.side_effect = [
            [
                self._route_row(22, 0, "ADL", total=3),
                self._route_row(22, 1, "PER", total=3),
            ],
            [],
            [],
        ]

        graphs, total = load_route_graph_page_with_total(limit=10, offset=20)

        self.assertEqual([graph.route.route_id for graph in graphs], [22])
        self.assertEqual(total, 3)
        fetch_all_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.routes.list_page_with_total, (10, 20)),
                call(cursor, QUERIES.trucks.list_assigned_by_routes, ([22],)),
                call(cursor, QUERIES.packages.list_assigned_by_routes, ([22],)),
            ]
        )

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graph_page_with_total_returns_empty_page_with_total(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.return_value = [
            {
                "route_id": None,
                "departure_time": None,
                "status": None,
                "truck_vehicle_id": None,
                "stop_order": None,
                "location_code": None,
                "total": 3,
            }
        ]

        graphs, total = load_route_graph_page_with_total(limit=10, offset=99)

        self.assertEqual(graphs, [])
        self.assertEqual(total, 3)
        fetch_all_tx_mock.assert_called_once_with(cursor, QUERIES.routes.list_page_with_total, (10, 99))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graphs_returns_empty_list_when_no_routes_exist(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.side_effect = [[], [], []]

        graphs = load_route_graphs()

        self.assertEqual(graphs, [])
        fetch_all_tx_mock.assert_called_once_with(cursor, QUERIES.routes.list_all)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_route_graphs_rejects_missing_assigned_truck(
        self,
        fetch_all_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        fetch_all_tx_mock.side_effect = [
            [
                self._route_row(21, 0, "SYD", truck_vehicle_id=1001),
                self._route_row(21, 1, "MEL", truck_vehicle_id=1001),
            ],
            [],
            [],
        ]

        with self.assertRaises(ValueError) as ctx:
            load_route_graphs()

        self.assertIn("Route 21 references missing truck 1001.", str(ctx.exception))

    def _transaction_cursor(self, transaction_cursor_mock: MagicMock) -> MagicMock:
        cursor = MagicMock()
        transaction_cursor_mock.return_value.__enter__.return_value = cursor
        return cursor

    def _route_row(
        self,
        route_id: int,
        stop_order: int,
        location_code: str,
        truck_vehicle_id: int | None = None,
        total: int | None = None,
    ) -> dict[str, object]:
        row: dict[str, object] = {
            "route_id": route_id,
            "departure_time": None,
            "status": RouteStatus.PLANNED.value,
            "truck_vehicle_id": truck_vehicle_id,
            "stop_order": stop_order,
            "location_code": location_code,
        }
        if total is not None:
            row["total"] = total
        return row

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

    def _joined_package_row(
        self,
        package_id: int,
        *,
        customer_id: int,
        route_id: int,
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
            "customer_name": f"Customer {customer_id}",
            "customer_email": f"customer{customer_id}@example.com",
            "customer_phone": f"04123456{customer_id:02d}",
        }
