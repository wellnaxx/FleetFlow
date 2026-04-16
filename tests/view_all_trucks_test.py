import unittest
from unittest.mock import Mock

from adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks


class TestViewAllTrucks_Should(unittest.TestCase):
    def setUp(self):
        self.mock_app_data = Mock()
        self.command = ViewAllTrucks(params={}, app_data=self.mock_app_data, auth=None)  # type: ignore[reportArgumentType]

    def test_no_trucks_exist(self):
        self.mock_app_data.view_all_trucks.return_value = []
        result = self.command.execute()
        self.assertEqual(result, "No trucks.")
        self.mock_app_data.view_all_trucks.assert_called_once()

    def test_with_multiple_trucks(self):
        mock_truck1 = Mock()
        mock_truck1.info.return_value = "Truck 1 Info"

        mock_truck2 = Mock()
        mock_truck2.info.return_value = "Truck 2 Info"

        self.mock_app_data.view_all_trucks.return_value = [mock_truck1, mock_truck2]

        expected_output = "Truck 1 Info\n\nTruck 2 Info"
        result = self.command.execute()
        self.assertEqual(result, expected_output)
        self.mock_app_data.view_all_trucks.assert_called_once()
