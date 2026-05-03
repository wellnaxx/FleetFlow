import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.truck_repository import PostgresTruckRepository
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus

MODULE = "src.adapters.driven.persistence.database.repositories.truck_repository"


class PostgresTruckRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = PostgresTruckRepository()

    @patch(f"{MODULE}.execute_write")
    def test_add_inserts_truck_state(self, execute_write_mock: MagicMock) -> None:
        truck = self._truck()

        self.repo.add(truck)

        execute_write_mock.assert_called_once_with(
            QUERIES.trucks.add,
            (
                1001,
                TruckModel.SCANIA.value,
                42000,
                8000,
                TruckStatus.ON_THE_WAY.value,
                "SYD",
                datetime(2026, 5, 1, 9, 0),
                datetime(2026, 5, 1, 17, 0),
                "MEL",
            ),
        )

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_truck")
    def test_list_fleet_maps_all_truck_rows(
        self,
        map_truck_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        rows = [self._truck_row(1001), self._truck_row(1002)]
        trucks = [self._truck(1001), self._truck(1002)]
        fetch_all_mock.return_value = rows
        map_truck_mock.side_effect = trucks

        result = self.repo.list_fleet()

        self.assertEqual(result, trucks)
        fetch_all_mock.assert_called_once_with(QUERIES.trucks.list_all)
        self.assertEqual([call.args[0] for call in map_truck_mock.call_args_list], rows)

    @patch(f"{MODULE}.fetch_one", return_value=None)
    @patch(f"{MODULE}.map_truck")
    def test_find_by_id_returns_none_when_truck_is_missing(
        self,
        map_truck_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        truck = self.repo.find_by_id(1001)

        self.assertIsNone(truck)
        fetch_one_mock.assert_called_once_with(QUERIES.trucks.get_by_id, (1001,))
        map_truck_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_one")
    @patch(f"{MODULE}.map_truck")
    def test_find_by_id_maps_existing_truck(
        self,
        map_truck_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        row = self._truck_row(1001)
        expected = self._truck()
        fetch_one_mock.return_value = row
        map_truck_mock.return_value = expected

        truck = self.repo.find_by_id(1001)

        self.assertIs(truck, expected)
        fetch_one_mock.assert_called_once_with(QUERIES.trucks.get_by_id, (1001,))
        map_truck_mock.assert_called_once_with(row)

    @patch(f"{MODULE}.execute_write")
    def test_update_state_writes_mutable_truck_state(self, execute_write_mock: MagicMock) -> None:
        truck = self._truck()

        self.repo.update_state(truck)

        execute_write_mock.assert_called_once_with(
            QUERIES.trucks.update_state,
            (
                TruckStatus.ON_THE_WAY.value,
                "SYD",
                datetime(2026, 5, 1, 9, 0),
                datetime(2026, 5, 1, 17, 0),
                "MEL",
                1001,
            ),
        )

    def _truck(self, vehicle_id: int = 1001) -> Truck:
        truck = Truck(vehicle_id, TruckModel.SCANIA, 42000, 8000)
        truck.status = TruckStatus.ON_THE_WAY
        truck.current_location = "SYD"
        truck.busy_from = datetime(2026, 5, 1, 9, 0)
        truck.busy_until = datetime(2026, 5, 1, 17, 0)
        truck.in_transit_to = "MEL"
        return truck

    def _truck_row(self, vehicle_id: int) -> dict[str, object]:
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
        }
