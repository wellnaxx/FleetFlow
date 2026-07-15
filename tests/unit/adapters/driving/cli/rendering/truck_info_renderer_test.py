import unittest

from src.adapters.driving.cli.rendering.truck_info_renderer import render_truck_info
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.value_objects.location_code import LocationCode


class TruckInfoRendererShould(unittest.TestCase):
    def test_render_truck_with_known_location(self) -> None:
        truck = Truck(vehicle_id=1001, name=TruckModel.SCANIA, capacity=42000, max_range=8000)
        truck.current_location = LocationCode("SYD")

        result = render_truck_info(truck)

        self.assertEqual(
            result,
            "Vehicle ID: 1001\n"
            f"Name: {TruckModel.SCANIA}\n"
            "Capacity: 42000\n"
            "Max range: 8000\n"
            f"Status: {truck.status}\n"
            "Location: SYD",
        )

    def test_render_truck_with_unknown_location(self) -> None:
        truck = Truck(vehicle_id=1001, name=TruckModel.SCANIA, capacity=42000, max_range=8000)

        result = render_truck_info(truck)

        self.assertEqual(
            result,
            "Vehicle ID: 1001\n"
            f"Name: {TruckModel.SCANIA}\n"
            "Capacity: 42000\n"
            "Max range: 8000\n"
            f"Status: {truck.status}\n"
            "Location: Unknown",
        )
