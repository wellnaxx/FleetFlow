import unittest
from unittest.mock import patch

from src.composition.seed_fleet import build_default_fleet, seed_fleet_if_empty
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel


class _TruckRepository:
    def __init__(self, trucks: list[Truck] | None = None) -> None:
        self.trucks = trucks or []

    def add(self, truck: Truck) -> None:
        self.trucks.append(truck)

    def list_fleet(self) -> list[Truck]:
        return list(self.trucks)

    def find_by_id(self, vehicle_id: int) -> Truck | None:
        return next((truck for truck in self.trucks if truck.vehicle_id == vehicle_id), None)

    def update_state(self, truck: Truck) -> None:
        pass


class SeedFleet_Should(unittest.TestCase):
    @patch("src.composition.seed_fleet.Map.get_locations", return_value=["L1", "L2", "L3"])
    def test_build_default_fleet_creates_and_disperses_fixed_fleet(self, _get_locs: object) -> None:
        fleet = build_default_fleet()

        self.assertEqual(len(fleet), 40)
        trucks_by_id = {truck.vehicle_id: truck for truck in fleet}
        self.assertEqual(trucks_by_id[1001].name, TruckModel.SCANIA)
        self.assertEqual(trucks_by_id[1011].name, TruckModel.MAN)
        self.assertEqual(trucks_by_id[1026].name, TruckModel.ACTROS)
        self.assertEqual(trucks_by_id[1001].current_location, "L1")
        self.assertEqual(trucks_by_id[1011].current_location, "L2")
        self.assertEqual(trucks_by_id[1026].current_location, "L3")

    @patch("src.composition.seed_fleet.Map.get_locations", return_value=["A"])
    def test_seed_fleet_if_empty_adds_default_fleet_to_empty_repo(self, _get_locs: object) -> None:
        repo = _TruckRepository()

        seed_fleet_if_empty(repo)

        self.assertEqual(len(repo.list_fleet()), 40)
        self.assertIsNotNone(repo.find_by_id(1001))

    @patch("src.composition.seed_fleet.Map.get_locations", return_value=["A"])
    def test_seed_fleet_if_empty_leaves_existing_repo_unchanged(self, _get_locs: object) -> None:
        existing = Truck(2001, TruckModel.SCANIA, 42000, 8000)
        repo = _TruckRepository([existing])

        seed_fleet_if_empty(repo)

        self.assertEqual(repo.list_fleet(), [existing])
