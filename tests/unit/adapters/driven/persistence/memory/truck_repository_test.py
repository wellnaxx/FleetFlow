import unittest
from typing import Any
from unittest.mock import patch

from src.adapters.driven.persistence.memory.truck_repository import InMemoryTruckRepository
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel


class InMemoryTruckRepository_Should(unittest.TestCase):
    @patch(
        "src.composition.seed_fleet.Map.get_locations",
        return_value=["L1", "L2", "L3"],
    )
    def test_init_builds_fleet_and_disperses_round_robin(self, _get_locs: Any) -> None:
        repo = InMemoryTruckRepository()

        self.assertEqual(len(repo.vehicles), 40)

        trucks_by_id = {truck.vehicle_id: truck for truck in repo.vehicles}
        self.assertEqual(trucks_by_id[1001].current_location, "L1")
        self.assertEqual(trucks_by_id[1011].current_location, "L2")
        self.assertEqual(trucks_by_id[1026].current_location, "L3")
        self.assertEqual(trucks_by_id[1002].current_location, "L1")
        self.assertEqual(trucks_by_id[1012].current_location, "L2")
        self.assertEqual(trucks_by_id[1027].current_location, "L3")

        self.assertTrue(all(truck.current_location in {"L1", "L2", "L3"} for truck in repo.vehicles))

    @patch("src.composition.seed_fleet.Map.get_locations", return_value=["A", "B"])
    def test_list_fleet_returns_copy_and_find_by_id(self, _get_locs: Any) -> None:
        repo = InMemoryTruckRepository()

        fleet = repo.list_fleet()
        fleet.pop()

        self.assertEqual(len(repo.vehicles), 40)
        self.assertIs(repo.find_by_id(repo.vehicles[0].vehicle_id), repo.vehicles[0])
        self.assertIsNone(repo.find_by_id(999999))

    @patch("src.composition.seed_fleet.Map.get_locations", return_value=["A"])
    def test_add_appends_truck_to_fleet(self, _get_locs: Any) -> None:
        repo = InMemoryTruckRepository()
        truck = Truck(2001, TruckModel.SCANIA, 42000, 8000)

        repo.add(truck)

        self.assertIs(repo.find_by_id(2001), truck)
        self.assertIs(repo.list_fleet()[-1], truck)

    @patch("src.composition.seed_fleet.Map.get_locations", return_value=["A"])
    def test_update_state_is_no_op_because_objects_are_shared(self, _get_locs: Any) -> None:
        repo = InMemoryTruckRepository()
        truck = repo.vehicles[0]

        repo.update_state(truck)

        self.assertIs(repo.find_by_id(truck.vehicle_id), truck)
