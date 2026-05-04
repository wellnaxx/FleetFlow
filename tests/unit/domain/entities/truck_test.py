import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode


class TestTruck_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_truck_data = {
            "vehicle_id": 1,
            "name": TruckModel.SCANIA,
            "capacity": 1000,
            "max_range": 500,
        }
        self.truck = Truck(**self.valid_truck_data)  # type: ignore[reportArgumentType]

    def test_init_with_valid_data(self) -> None:
        for model in TruckModel:
            with self.subTest(model=model):
                truck = Truck(vehicle_id=1, name=model, capacity=1000, max_range=500)

                self.assertEqual(truck.vehicle_id, 1)
                self.assertEqual(truck.name, model)
                self.assertEqual(truck.capacity, 1000)
                self.assertEqual(truck.max_range, 500)
                self.assertEqual(truck.status, TruckStatus.FREE)
                self.assertIsNone(truck.current_location)
                self.assertIsNone(truck.route)
                self.assertIsNone(truck.busy_from)
                self.assertIsNone(truck.busy_until)
                self.assertIsNone(truck.in_transit_to)

    def test_init_with_invalid_name(self) -> None:
        with self.assertRaises(ValueError) as context:
            Truck(vehicle_id=1, name="Invalid", capacity=1000, max_range=500)

        self.assertEqual(str(context.exception), f"Truck name must be {TruckModel.labels()}")

    def test_init_capacity_and_range_conversion(self) -> None:
        truck = Truck(
            vehicle_id=1,
            name=TruckModel.SCANIA,
            capacity=1000,
            max_range=500,
        )  # type: ignore[reportArgumentType]

        self.assertEqual(truck.capacity, 1000)
        self.assertEqual(truck.max_range, 500)
        self.assertIsInstance(truck.capacity, int)
        self.assertIsInstance(truck.max_range, int)

    def test_is_free_when_free(self) -> None:
        self.truck.status = TruckStatus.FREE

        self.assertTrue(self.truck.is_free())

    def test_is_free_when_not_free(self) -> None:
        self.truck.status = TruckStatus.ON_THE_WAY

        self.assertFalse(self.truck.is_free())

    def test_assign(self) -> None:
        mock_route = Mock()
        mock_route.departure_time = datetime(2024, 1, 1, 10, 0)
        mock_route.eta_final = datetime(2024, 1, 1, 18, 0)

        self.truck.assign(mock_route)

        self.assertEqual(self.truck.route, mock_route)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(self.truck.busy_from, mock_route.departure_time)
        self.assertEqual(self.truck.busy_until, mock_route.eta_final)
        self.assertIsNone(self.truck.in_transit_to)

    def test_assign_without_start_location(self) -> None:
        mock_route = Mock()
        mock_route.departure_time = datetime(2024, 1, 1, 10, 0)
        mock_route.eta_final = datetime(2024, 1, 1, 18, 0)

        self.truck.assign(mock_route)

        self.assertEqual(self.truck.route, mock_route)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)

    def test_release_with_no_route(self) -> None:
        self.truck.route = None
        self.truck.status = TruckStatus.ON_THE_WAY

        result = self.truck.release()

        self.assertFalse(result)
        self.assertEqual(self.truck.status, TruckStatus.FREE)
        self.assertIsNone(self.truck.in_transit_to)
        self.assertIsNone(self.truck.busy_from)
        self.assertIsNone(self.truck.busy_until)

    def test_release_force_true(self) -> None:
        mock_route = Mock()
        mock_route.end_location = LocationCode("MEL")
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY
        self.truck.current_location = LocationCode("SYD")

        result = self.truck.release(force=True)

        self.assertTrue(result)
        self.assertEqual(self.truck.current_location, LocationCode("MEL"))
        self.assertIsNone(self.truck.route)
        self.assertEqual(self.truck.status, TruckStatus.FREE)
        self.assertIsNone(self.truck.in_transit_to)
        self.assertIsNone(self.truck.busy_from)
        self.assertIsNone(self.truck.busy_until)

    def test_release_force_true_no_end_location(self) -> None:
        mock_route = Mock()
        mock_route.end_location = None
        self.truck.route = mock_route
        self.truck.current_location = LocationCode("SYD")

        result = self.truck.release(force=True)

        self.assertTrue(result)
        self.assertEqual(self.truck.current_location, LocationCode("SYD"))
        self.assertIsNone(self.truck.route)

    def test_release_force_false_before_eta(self) -> None:
        mock_route = Mock()
        mock_route.eta_final = datetime(2024, 1, 1, 18, 0)
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY

        now = datetime(2024, 1, 1, 15, 0)

        result = self.truck.release(force=False, now=now)

        self.assertFalse(result)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(self.truck.route, mock_route)

    def test_release_force_false_after_eta(self) -> None:
        mock_route = Mock()
        mock_route.eta_final = datetime(2024, 1, 1, 18, 0)
        mock_route.end_location = LocationCode("MEL")
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY
        self.truck.current_location = LocationCode("SYD")

        now = datetime(2024, 1, 1, 19, 0)

        result = self.truck.release(force=False, now=now)

        self.assertTrue(result)
        self.assertEqual(self.truck.current_location, LocationCode("MEL"))
        self.assertIsNone(self.truck.route)
        self.assertEqual(self.truck.status, TruckStatus.FREE)

    def test_release_force_false_no_eta_final(self) -> None:
        mock_route = Mock()
        mock_route.eta_final = None
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY

        result = self.truck.release(force=False)

        self.assertFalse(result)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(self.truck.route, mock_route)

    def test_release_force_false_without_now_parameter(self) -> None:
        mock_route = Mock()
        mock_route.eta_final = datetime.now() + timedelta(hours=1)
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY

        result = self.truck.release(force=False)

        self.assertFalse(result)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)

    def test_snapshot_state_restores_mutable_assignment_state(self) -> None:
        mock_route = Mock()
        busy_from = datetime(2024, 1, 1, 10, 0)
        busy_until = datetime(2024, 1, 1, 18, 0)
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY
        self.truck.current_location = LocationCode("SYD")
        self.truck.busy_from = busy_from
        self.truck.busy_until = busy_until
        self.truck.in_transit_to = LocationCode("MEL")
        snapshot = self.truck.snapshot_state()

        self.truck.route = None
        self.truck.status = TruckStatus.FREE
        self.truck.current_location = None
        self.truck.busy_from = None
        self.truck.busy_until = None
        self.truck.in_transit_to = None

        self.truck.restore_state(snapshot)

        self.assertIs(self.truck.route, mock_route)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(self.truck.current_location, LocationCode("SYD"))
        self.assertEqual(self.truck.busy_from, busy_from)
        self.assertEqual(self.truck.busy_until, busy_until)
        self.assertEqual(self.truck.in_transit_to, LocationCode("MEL"))

    def test_info(self) -> None:
        self.truck.current_location = LocationCode("SYD")

        result = self.truck.info()

        expected_info = (
            f"Vehicle ID: {self.truck.vehicle_id}\n"
            f"Name: {self.truck.name}\n"
            f"Capacity: {self.truck.capacity}\n"
            f"Max range: {self.truck.max_range}\n"
            f"Status: {self.truck.status}\n"
            f"Location: SYD"
        )
        self.assertEqual(result, expected_info)

    def test_info_with_unknown_location(self) -> None:
        self.truck.current_location = None

        result = self.truck.info()

        self.assertIn("Location: Unknown", result)


if __name__ == "__main__":
    unittest.main()
