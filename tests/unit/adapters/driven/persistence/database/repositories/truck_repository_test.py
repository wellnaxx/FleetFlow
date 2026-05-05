import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.truck_repository import PostgresTruckRepository
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode

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

    @patch(f"{MODULE}.load_world_graph")
    def test_list_fleet_maps_all_truck_rows(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        trucks = [self._truck(1001), self._truck(1002)]
        load_world_graph_mock.return_value = SimpleNamespace(trucks={1001: trucks[0], 1002: trucks[1]})

        result = self.repo.list_fleet()

        self.assertEqual(result, trucks)
        load_world_graph_mock.assert_called_once_with()

    @patch(f"{MODULE}.load_world_graph")
    def test_find_by_id_returns_none_when_truck_is_missing(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        load_world_graph_mock.return_value = SimpleNamespace(trucks={})

        truck = self.repo.find_by_id(1001)

        self.assertIsNone(truck)
        load_world_graph_mock.assert_called_once_with()

    @patch(f"{MODULE}.load_world_graph")
    def test_find_by_id_maps_existing_truck(
        self,
        load_world_graph_mock: MagicMock,
    ) -> None:
        expected = self._truck()
        load_world_graph_mock.return_value = SimpleNamespace(trucks={1001: expected})

        truck = self.repo.find_by_id(1001)

        self.assertIs(truck, expected)
        load_world_graph_mock.assert_called_once_with()

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
        truck.current_location = LocationCode("SYD")
        truck.busy_from = datetime(2026, 5, 1, 9, 0)
        truck.busy_until = datetime(2026, 5, 1, 17, 0)
        truck.in_transit_to = LocationCode("MEL")
        return truck
