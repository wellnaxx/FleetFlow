import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.route_repository import PostgresRouteRepository
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.route_status import RouteStatus
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
        self.assertEqual(route.locations, ["SYD", "MEL", "ADL"])
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

    @patch(f"{MODULE}.fetch_all", return_value=[])
    @patch(f"{MODULE}.map_route")
    def test_get_by_id_returns_none_when_route_is_missing(
        self,
        map_route_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        route = self.repo.get_by_id(21)

        self.assertIsNone(route)
        fetch_all_mock.assert_called_once_with(QUERIES.routes.get_by_id, (21,))
        map_route_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_route")
    def test_get_by_id_maps_route_rows(
        self,
        map_route_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        rows = [self._route_stop_row(21, 0, "SYD"), self._route_stop_row(21, 1, "MEL")]
        expected = DeliveryRoute("SYD", "MEL", route_id=21)
        fetch_all_mock.return_value = rows
        map_route_mock.return_value = expected

        route = self.repo.get_by_id(21)

        self.assertIs(route, expected)
        fetch_all_mock.assert_called_once_with(QUERIES.routes.get_by_id, (21,))
        map_route_mock.assert_called_once_with(rows)

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_route")
    def test_list_all_groups_rows_by_route_id(
        self,
        map_route_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        route_1_rows = [self._route_stop_row(21, 0, "SYD"), self._route_stop_row(21, 1, "MEL")]
        route_2_rows = [self._route_stop_row(22, 0, "MEL"), self._route_stop_row(22, 1, "ADL")]
        route_1 = DeliveryRoute("SYD", "MEL", route_id=21)
        route_2 = DeliveryRoute("MEL", "ADL", route_id=22)
        fetch_all_mock.return_value = [*route_1_rows, *route_2_rows]
        map_route_mock.side_effect = [route_1, route_2]

        routes = self.repo.list_all()

        self.assertEqual(routes, [route_1, route_2])
        fetch_all_mock.assert_called_once_with(QUERIES.routes.list_all)
        map_route_mock.assert_has_calls([call(route_1_rows), call(route_2_rows)])

    @patch(f"{MODULE}.fetch_all")
    def test_list_all_rejects_invalid_route_id_type(self, fetch_all_mock: MagicMock) -> None:
        fetch_all_mock.return_value = [
            {
                "route_id": "21",
                "departure_time": None,
                "status": "PLANNED",
                "truck_vehicle_id": None,
                "stop_order": 0,
                "location_code": "SYD",
            }
        ]

        with self.assertRaises(TypeError) as ctx:
            self.repo.list_all()

        self.assertIn("route_id: expected int", str(ctx.exception))

    def _route_stop_row(self, route_id: int, stop_order: int, location_code: str) -> dict[str, object]:
        return {
            "route_id": route_id,
            "departure_time": None,
            "status": "PLANNED",
            "truck_vehicle_id": None,
            "stop_order": stop_order,
            "location_code": location_code,
        }
