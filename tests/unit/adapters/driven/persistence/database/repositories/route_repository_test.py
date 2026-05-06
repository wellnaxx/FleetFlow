import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.route_repository import PostgresRouteRepository
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_model import TruckModel
from src.domain.value_objects.location_code import LocationCode

MODULE = "src.adapters.driven.persistence.database.repositories.route_repository"


class PostgresRouteRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = PostgresRouteRepository()

    @patch(f"{MODULE}.execute_write_tx")
    @patch(f"{MODULE}.execute_insert_tx", return_value=42)
    @patch(f"{MODULE}.transaction_cursor")
    def test_create_inserts_route_and_stops_in_transaction(
        self,
        transaction_cursor_mock: MagicMock,
        execute_insert_tx_mock: MagicMock,
        execute_write_tx_mock: MagicMock,
    ) -> None:
        cursor = object()
        transaction_cursor_mock.return_value.__enter__.return_value = cursor

        route = self.repo.create(
            locations=["syd", LocationCode("mel"), "ADL"],
            departure_time=None,
        )

        transaction_cursor_mock.assert_called_once_with()
        execute_insert_tx_mock.assert_called_once_with(
            cursor,
            QUERIES.routes.add,
            (None, RouteStatus.PLANNED.value),
        )
        execute_write_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.routes.add_stop, (42, 0, "SYD")),
                call(cursor, QUERIES.routes.add_stop, (42, 1, "MEL")),
                call(cursor, QUERIES.routes.add_stop, (42, 2, "ADL")),
            ]
        )
        self.assertEqual(route.route_id, 42)
        self.assertEqual(route.locations, [LocationCode("SYD"), LocationCode("MEL"), LocationCode("ADL")])
        self.assertIsNone(route.departure_time)
        self.assertEqual(route.status, RouteStatus.PLANNED)

    @patch(f"{MODULE}.execute_write_tx")
    @patch(f"{MODULE}.execute_insert_tx", return_value=42)
    @patch(f"{MODULE}.transaction_cursor")
    def test_create_persists_scheduled_status_when_departure_is_set(
        self,
        transaction_cursor_mock: MagicMock,
        execute_insert_tx_mock: MagicMock,
        execute_write_tx_mock: MagicMock,
    ) -> None:
        cursor = object()
        departure_time = datetime(2026, 5, 2, 9, 0)
        transaction_cursor_mock.return_value.__enter__.return_value = cursor

        route = self.repo.create(
            locations=["SYD", "MEL"],
            departure_time=departure_time,
        )

        execute_insert_tx_mock.assert_called_once_with(
            cursor,
            QUERIES.routes.add,
            (departure_time, RouteStatus.SCHEDULED.value),
        )
        self.assertEqual(execute_write_tx_mock.call_count, 2)
        self.assertIs(route.departure_time, departure_time)
        self.assertEqual(route.status, RouteStatus.SCHEDULED)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.execute_insert_tx")
    @patch(f"{MODULE}.execute_write_tx")
    def test_create_validates_route_before_opening_transaction(
        self,
        execute_write_tx_mock: MagicMock,
        execute_insert_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        with self.assertRaises(ValueError):
            self.repo.create(locations=["SYD"], departure_time=None)

        transaction_cursor_mock.assert_not_called()
        execute_insert_tx_mock.assert_not_called()
        execute_write_tx_mock.assert_not_called()

    @patch(f"{MODULE}.execute_write")
    def test_remove_deletes_route_by_id(self, execute_write_mock: MagicMock) -> None:
        self.repo.remove(21)

        execute_write_mock.assert_called_once_with(QUERIES.routes.remove, (21,))

    @patch(f"{MODULE}.load_route_graph")
    def test_get_by_id_returns_none_when_route_is_missing(
        self,
        load_route_graph_mock: MagicMock,
    ) -> None:
        load_route_graph_mock.return_value = None

        route = self.repo.get_by_id(21)

        self.assertIsNone(route)
        load_route_graph_mock.assert_called_once_with(21)

    @patch(f"{MODULE}.load_route_graph")
    def test_get_by_id_returns_hydrated_route(
        self,
        load_route_graph_mock: MagicMock,
    ) -> None:
        expected = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)
        load_route_graph_mock.return_value = SimpleNamespace(route=expected)

        route = self.repo.get_by_id(21)

        self.assertIs(route, expected)
        load_route_graph_mock.assert_called_once_with(21)

    @patch(f"{MODULE}.load_route_graphs")
    def test_list_all_returns_hydrated_routes(
        self,
        load_route_graphs_mock: MagicMock,
    ) -> None:
        route_1 = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)
        route_2 = DeliveryRoute(LocationCode("MEL"), LocationCode("ADL"), route_id=22)
        load_route_graphs_mock.return_value = [
            SimpleNamespace(route=route_1),
            SimpleNamespace(route=route_2),
        ]

        routes = self.repo.list_all()

        self.assertEqual(routes, [route_1, route_2])
        load_route_graphs_mock.assert_called_once_with()

    @patch(f"{MODULE}.load_route_graphs")
    def test_list_all_propagates_graph_loader_errors(
        self,
        load_route_graphs_mock: MagicMock,
    ) -> None:
        load_route_graphs_mock.side_effect = TypeError("route_id: expected int")

        with self.assertRaises(TypeError) as ctx:
            self.repo.list_all()

        self.assertIn("route_id: expected int", str(ctx.exception))

    @patch(f"{MODULE}.execute_write")
    def test_update_state_writes_mutable_route_state(self, execute_write_mock: MagicMock) -> None:
        departure_time = datetime(2026, 5, 2, 9, 0)
        route = DeliveryRoute(
            LocationCode("SYD"), LocationCode("MEL"), departure_time=departure_time, route_id=21
        )
        route.status = RouteStatus.IN_PROGRESS
        route.truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)

        self.repo.update_state(route)

        execute_write_mock.assert_called_once_with(
            QUERIES.routes.update_state,
            (
                departure_time,
                RouteStatus.IN_PROGRESS.value,
                1001,
                21,
            ),
        )

    @patch(f"{MODULE}.execute_write")
    def test_update_state_writes_null_truck_when_route_has_no_truck(
        self,
        execute_write_mock: MagicMock,
    ) -> None:
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=21)

        self.repo.update_state(route)

        execute_write_mock.assert_called_once_with(
            QUERIES.routes.update_state,
            (
                None,
                RouteStatus.PLANNED.value,
                None,
                21,
            ),
        )
