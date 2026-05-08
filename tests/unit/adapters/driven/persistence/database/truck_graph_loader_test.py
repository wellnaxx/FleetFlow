import unittest
from datetime import datetime
from types import MappingProxyType
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.graph_loaders.route_graph_loader import HydratedRouteGraph
from src.adapters.driven.persistence.database.graph_loaders.truck_graph_loader import (
    load_truck_graph,
    load_truck_graphs,
)
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode

MODULE = "src.adapters.driven.persistence.database.graph_loaders.truck_graph_loader"


class TruckGraphLoaderShould(unittest.TestCase):
    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_truck_graph_returns_none_when_truck_is_missing(
        self,
        fetch_one_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        fetch_one_tx_mock.return_value = None

        graph = load_truck_graph(1001)

        self.assertIsNone(graph)
        fetch_one_tx_mock.assert_called_once_with(cursor, QUERIES.trucks.get_by_id_with_route, (1001,))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_truck_graph_maps_free_truck_without_route_hydration(
        self,
        fetch_one_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        fetch_one_tx_mock.return_value = self._truck_row(1001, route_id=None)
        self._transaction_cursor(transaction_cursor_mock)

        graph = load_truck_graph(1001)

        self.assertIsNotNone(graph)
        assert graph is not None
        self.assertEqual(graph.truck.vehicle_id, 1001)
        self.assertIsNone(graph.truck.route)
        self.assertIsNone(graph.route)
        load_route_graph_tx_mock.assert_not_called()

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_truck_graph_returns_route_owned_truck_when_assigned(
        self,
        fetch_one_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)
        truck = self._truck(1001)
        route.truck = truck
        truck.route = route

        fetch_one_tx_mock.return_value = self._truck_row(1001, route_id=21)
        load_route_graph_tx_mock.return_value = self._route_graph(route, truck)

        graph = load_truck_graph(1001)

        self.assertIsNotNone(graph)
        assert graph is not None
        self.assertIs(graph.truck, truck)
        self.assertIs(graph.route, route)
        load_route_graph_tx_mock.assert_called_once_with(cursor, 21)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_all_tx")
    def test_load_truck_graphs_maps_all_trucks_ordered_by_vehicle_id(
        self,
        fetch_all_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)
        assigned_truck = self._truck(1001)
        route.truck = assigned_truck
        assigned_truck.route = route

        fetch_all_tx_mock.return_value = [
            self._truck_row(1002, route_id=None),
            self._truck_row(1001, route_id=21),
        ]
        load_route_graph_tx_mock.return_value = self._route_graph(route, assigned_truck)

        graphs = load_truck_graphs()

        self.assertEqual([graph.truck.vehicle_id for graph in graphs], [1001, 1002])
        self.assertIs(graphs[0].truck, assigned_truck)
        self.assertIsNone(graphs[1].route)
        fetch_all_tx_mock.assert_called_once_with(cursor, QUERIES.trucks.list_all_with_route)
        load_route_graph_tx_mock.assert_called_once_with(cursor, 21)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_truck_graph_raises_when_assigned_route_is_missing(
        self,
        fetch_one_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        fetch_one_tx_mock.return_value = self._truck_row(1001, route_id=21)
        load_route_graph_tx_mock.return_value = None

        with self.assertRaises(ValueError) as ctx:
            load_truck_graph(1001)

        self.assertIn("Truck 1001 references missing route 21.", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.load_route_graph_tx")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_truck_graph_raises_when_route_graph_omits_assigned_truck(
        self,
        fetch_one_tx_mock: MagicMock,
        load_route_graph_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)

        fetch_one_tx_mock.return_value = self._truck_row(1001, route_id=21)
        load_route_graph_tx_mock.return_value = self._route_graph(route, None)

        with self.assertRaises(ValueError) as ctx:
            load_truck_graph(1001)

        self.assertIn("Truck 1001 has route_id=21 in the database", str(ctx.exception))

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.fetch_one_tx")
    def test_load_truck_graph_rejects_invalid_route_id_type(
        self,
        fetch_one_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        row = self._truck_row(1001, route_id=21)
        row["route_id"] = True
        fetch_one_tx_mock.return_value = row

        with self.assertRaises(TypeError) as ctx:
            load_truck_graph(1001)

        self.assertIn("route_id: expected int or None", str(ctx.exception))

    def _transaction_cursor(self, transaction_cursor_mock: MagicMock) -> MagicMock:
        cursor = MagicMock()
        transaction_cursor_mock.return_value.__enter__.return_value = cursor
        return cursor

    def _route_graph(
        self,
        route: DeliveryRoute,
        truck: Truck | None,
    ) -> HydratedRouteGraph:
        return HydratedRouteGraph(
            route=route,
            truck=truck,
            packages=MappingProxyType({}),
            customers=MappingProxyType({}),
        )

    def _truck(self, vehicle_id: int) -> Truck:
        truck = Truck(vehicle_id, TruckModel.SCANIA, 42000, 8000)
        truck.status = TruckStatus.ON_THE_WAY
        truck.current_location = LocationCode("SYD")
        truck.busy_from = datetime(2026, 5, 1, 9, 0)
        truck.busy_until = datetime(2026, 5, 1, 17, 0)
        truck.in_transit_to = LocationCode("MEL")
        return truck

    def _truck_row(self, vehicle_id: int, *, route_id: int | None) -> dict[str, object]:
        return {
            "vehicle_id": vehicle_id,
            "name": TruckModel.SCANIA.value,
            "capacity": 42000,
            "max_range": 8000,
            "status": TruckStatus.ON_THE_WAY.value,
            "current_location": "SYD",
            "busy_from": datetime(2026, 5, 1, 9, 0),
            "busy_until": datetime(2026, 5, 1, 17, 0),
            "in_transit_to": "MEL",
            "route_id": route_id,
        }
