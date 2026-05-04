import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.truck_unit_of_work_repository import (
    PostgresTruckUnitOfWorkRepository,
)
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus

MODULE = "src.adapters.driven.persistence.database.repositories.truck_unit_of_work_repository"


class PostgresTruckUnitOfWorkRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = MagicMock()
        self.repo = PostgresTruckUnitOfWorkRepository(self.cursor)

    @patch(f"{MODULE}.execute_write_tx")
    def test_update_state_writes_truck_state_with_shared_cursor(self, execute_write_tx_mock: MagicMock) -> None:
        execute_write_tx_mock.return_value = 1
        busy_from = datetime(2026, 5, 2, 9, 0)
        busy_until = datetime(2026, 5, 2, 17, 0)
        truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)
        truck.status = TruckStatus.ON_THE_WAY
        truck.current_location = "SYD"
        truck.busy_from = busy_from
        truck.busy_until = busy_until
        truck.in_transit_to = "MEL"

        self.repo.update_state(truck)

        execute_write_tx_mock.assert_called_once_with(
            self.cursor,
            QUERIES.trucks.update_state,
            (TruckStatus.ON_THE_WAY.value, "SYD", busy_from, busy_until, "MEL", 1001),
        )

    @patch(f"{MODULE}.execute_write_tx")
    def test_update_state_writes_null_locations_with_shared_cursor(
        self,
        execute_write_tx_mock: MagicMock,
    ) -> None:
        execute_write_tx_mock.return_value = 1
        truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)

        self.repo.update_state(truck)

        execute_write_tx_mock.assert_called_once_with(
            self.cursor,
            QUERIES.trucks.update_state,
            (TruckStatus.FREE.value, None, None, None, None, 1001),
        )

    @patch(f"{MODULE}.execute_write_tx")
    def test_update_state_propagates_write_errors(self, execute_write_tx_mock: MagicMock) -> None:
        error = RuntimeError("write failed")
        execute_write_tx_mock.side_effect = error
        truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)
        truck.status = TruckStatus.ON_THE_WAY
        truck.current_location = "SYD"
        truck.in_transit_to = "MEL"

        with self.assertRaises(RuntimeError) as ctx:
            self.repo.update_state(truck)

        self.assertIs(ctx.exception, error)
        execute_write_tx_mock.assert_called_once_with(
            self.cursor,
            QUERIES.trucks.update_state,
            (TruckStatus.ON_THE_WAY.value, "SYD", None, None, "MEL", 1001),
        )

    @patch(f"{MODULE}.execute_write_tx")
    def test_update_state_raises_when_truck_row_is_missing(self, execute_write_tx_mock: MagicMock) -> None:
        execute_write_tx_mock.return_value = 0
        truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)

        with self.assertRaises(ValueError) as ctx:
            self.repo.update_state(truck)

        self.assertIn("Expected to update one truck row for id 1001, affected 0", str(ctx.exception))
