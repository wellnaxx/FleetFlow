import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.route_unit_of_work_repository import (
    PostgresRouteUnitOfWorkRepository,
)
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_model import TruckModel

MODULE = "src.adapters.driven.persistence.database.repositories.route_unit_of_work_repository"


class PostgresRouteUnitOfWorkRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = MagicMock()
        self.repo = PostgresRouteUnitOfWorkRepository(self.cursor)

    @patch(f"{MODULE}.execute_write_tx")
    def test_update_state_writes_route_state_with_shared_cursor(self, execute_write_tx_mock: MagicMock) -> None:
        execute_write_tx_mock.return_value = 1
        departure_time = datetime(2026, 5, 2, 9, 0)
        route = DeliveryRoute("SYD", "MEL", departure_time=departure_time, route_id=21)
        route.status = RouteStatus.IN_PROGRESS
        route.truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)

        self.repo.update_state(route)

        execute_write_tx_mock.assert_called_once_with(
            self.cursor,
            QUERIES.routes.update_state,
            (departure_time, RouteStatus.IN_PROGRESS.value, 1001, 21),
        )

    @patch(f"{MODULE}.execute_write_tx")
    def test_remove_deletes_route_with_shared_cursor(self, execute_write_tx_mock: MagicMock) -> None:
        execute_write_tx_mock.return_value = 1
        self.repo.remove(21)

        execute_write_tx_mock.assert_called_once_with(self.cursor, QUERIES.routes.remove, (21,))

    @patch(f"{MODULE}.execute_write_tx")
    def test_update_state_raises_when_route_row_is_missing(self, execute_write_tx_mock: MagicMock) -> None:
        execute_write_tx_mock.return_value = 0
        route = DeliveryRoute("SYD", "MEL", route_id=21)

        with self.assertRaises(ValueError) as ctx:
            self.repo.update_state(route)

        self.assertIn("Expected to update one route row for id 21, affected 0", str(ctx.exception))

    @patch(f"{MODULE}.execute_write_tx")
    def test_remove_raises_when_route_row_is_missing(self, execute_write_tx_mock: MagicMock) -> None:
        execute_write_tx_mock.return_value = 0

        with self.assertRaises(ValueError) as ctx:
            self.repo.remove(21)

        self.assertIn("Expected to remove one route row for id 21, affected 0", str(ctx.exception))
