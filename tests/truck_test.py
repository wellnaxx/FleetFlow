import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus


class TestTruck_Should(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.valid_truck_data = {"vehicle_id": 1, "name": "Scania", "capacity": 1000, "max_range": 500}
        self.truck = Truck(**self.valid_truck_data)  # type: ignore[reportArgumentType]

    def test_init_with_valid_data(self):
        """Test initialization with valid data."""
        # Test valid truck names
        for name in ["Scania", "Man", "Actros"]:
            with self.subTest(name=name):
                truck = Truck(vehicle_id=1, name=name, capacity=1000, max_range=500)
                self.assertEqual(truck.vehicle_id, 1)
                self.assertEqual(truck.name, name)
                self.assertEqual(truck.capacity, 1000)
                self.assertEqual(truck.max_range, 500)
                self.assertEqual(truck.status, TruckStatus.FREE)
                self.assertIsNone(truck.current_location)
                self.assertIsNone(truck.route)
                self.assertIsNone(truck.busy_from)
                self.assertIsNone(truck.busy_until)
                self.assertIsNone(truck.in_transit_to)

    def test_init_with_invalid_name(self):
        """Test initialization with invalid truck name."""
        with self.assertRaises(ValueError) as context:
            Truck(vehicle_id=1, name="Invalid", capacity=1000, max_range=500)
        self.assertEqual(str(context.exception), "Truck name must be Scania, Man or Actros")

    def test_init_capacity_and_range_conversion(self):
        """Test that capacity and max_range are converted to int."""
        truck = Truck(vehicle_id=1, name="Scania", capacity="1000", max_range="500")  # type: ignore[reportArgumentType]
        self.assertEqual(truck.capacity, 1000)
        self.assertEqual(truck.max_range, 500)
        self.assertIsInstance(truck.capacity, int)
        self.assertIsInstance(truck.max_range, int)

    def test_is_free_when_free(self):
        """Test is_free() when truck status is FREE."""
        self.truck.status = TruckStatus.FREE
        self.assertTrue(self.truck.is_free())

    def test_is_free_when_not_free(self):
        """Test is_free() when truck status is not FREE."""
        self.truck.status = TruckStatus.ON_THE_WAY
        self.assertFalse(self.truck.is_free())

    def test_assign(self):
        """Test assign() method."""
        # Arrange
        mock_route = Mock()
        mock_route.departure_time = datetime(2024, 1, 1, 10, 0)
        mock_route.eta_final = datetime(2024, 1, 1, 18, 0)
        start_location = "Sofia"

        # Act
        self.truck.assign(mock_route, start_location)

        # Assert
        self.assertEqual(self.truck.route, mock_route)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(self.truck.busy_from, mock_route.departure_time)
        self.assertEqual(self.truck.busy_until, mock_route.eta_final)
        self.assertIsNone(self.truck.in_transit_to)

    def test_assign_without_start_location(self):
        """Test assign() method without start location."""
        # Arrange
        mock_route = Mock()
        mock_route.departure_time = datetime(2024, 1, 1, 10, 0)
        mock_route.eta_final = datetime(2024, 1, 1, 18, 0)

        # Act
        self.truck.assign(mock_route)

        # Assert
        self.assertEqual(self.truck.route, mock_route)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)

    def test_release_with_no_route(self):
        """Test release() when truck has no route assigned."""
        # Arrange
        self.truck.route = None
        self.truck.status = TruckStatus.ON_THE_WAY  # Simulate inconsistent state

        # Act
        result = self.truck.release()

        # Assert
        self.assertFalse(result)
        self.assertEqual(self.truck.status, TruckStatus.FREE)
        self.assertIsNone(self.truck.in_transit_to)
        self.assertIsNone(self.truck.busy_from)
        self.assertIsNone(self.truck.busy_until)

    def test_release_force_true(self):
        """Test release() with force=True."""
        # Arrange
        mock_route = Mock()
        mock_route.end_location = "Varna"
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY
        self.truck.current_location = "Sofia"

        # Act
        result = self.truck.release(force=True)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.truck.current_location, "Varna")
        self.assertIsNone(self.truck.route)
        self.assertEqual(self.truck.status, TruckStatus.FREE)
        self.assertIsNone(self.truck.in_transit_to)
        self.assertIsNone(self.truck.busy_from)
        self.assertIsNone(self.truck.busy_until)

    def test_release_force_true_no_end_location(self):
        """Test release() with force=True but route has no end_location."""
        # Arrange
        mock_route = Mock()
        mock_route.end_location = None
        self.truck.route = mock_route
        self.truck.current_location = "Sofia"

        # Act
        result = self.truck.release(force=True)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.truck.current_location, "Sofia")  # Should remain unchanged
        self.assertIsNone(self.truck.route)

    def test_release_force_false_before_eta(self):
        """Test release() with force=False when now < eta_final."""
        # Arrange
        mock_route = Mock()
        mock_route.eta_final = datetime(2024, 1, 1, 18, 0)
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY

        now = datetime(2024, 1, 1, 15, 0)  # Before eta_final

        # Act
        result = self.truck.release(force=False, now=now)

        # Assert
        self.assertFalse(result)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(self.truck.route, mock_route)

    def test_release_force_false_after_eta(self):
        """Test release() with force=False when now >= eta_final."""
        # Arrange
        mock_route = Mock()
        mock_route.eta_final = datetime(2024, 1, 1, 18, 0)
        mock_route.end_location = "Varna"
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY
        self.truck.current_location = "Sofia"

        now = datetime(2024, 1, 1, 19, 0)  # After eta_final

        # Act
        result = self.truck.release(force=False, now=now)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.truck.current_location, "Varna")
        self.assertIsNone(self.truck.route)
        self.assertEqual(self.truck.status, TruckStatus.FREE)

    def test_release_force_false_no_eta_final(self):
        """Test release() with force=False when route has no eta_final."""
        # Arrange
        mock_route = Mock()
        del mock_route.eta_final  # Remove eta_final attribute
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY

        # Act
        result = self.truck.release(force=False)

        # Assert
        self.assertFalse(result)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(self.truck.route, mock_route)

    def test_release_force_false_without_now_parameter(self):
        """Test release() with force=False without providing now parameter."""
        # Arrange
        mock_route = Mock()
        mock_route.eta_final = datetime.now() + timedelta(hours=1)  # Future time
        self.truck.route = mock_route
        self.truck.status = TruckStatus.ON_THE_WAY

        # Act
        result = self.truck.release(force=False)

        # Assert
        self.assertFalse(result)
        self.assertEqual(self.truck.status, TruckStatus.ON_THE_WAY)

    def test_info(self):
        """Test info() method."""
        # Arrange
        self.truck.current_location = "Sofia"

        # Act
        result = self.truck.info()

        # Assert
        expected_info = (
            f"Vehicle ID: {self.truck.vehicle_id}\n"
            f"Name: {self.truck.name}\n"
            f"Capacity: {self.truck.capacity}\n"
            f"Max range: {self.truck.max_range}\n"
            f"Status: {self.truck.status}\n"
            f"Location: Sofia"
        )
        self.assertEqual(result, expected_info)

    def test_info_with_unknown_location(self):
        """Test info() method when location is unknown."""
        # Arrange
        self.truck.current_location = None

        # Act
        result = self.truck.info()

        # Assert
        self.assertIn("Location: Unknown", result)


if __name__ == "__main__":
    unittest.main()
