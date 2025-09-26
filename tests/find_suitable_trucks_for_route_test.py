import unittest
from unittest.mock import Mock
from src.commands.find_suitable_trucks_for_route import FindSuitableTrucksForRoute

class TestFindSuitableTrucksForRoute_Should(unittest.TestCase):
    def test_with_none_param_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            cmd = FindSuitableTrucksForRoute([], app_data, auth).execute()

    def test_str_param_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            cmd = FindSuitableTrucksForRoute(["str"], app_data, auth).execute()

    def test_no_found_route_command(self):
        app_data = Mock()
        auth = Mock()
        app_data.find_route.return_value = None
        with self.assertRaises(ValueError):
            FindSuitableTrucksForRoute(["777"], app_data, auth).execute()

    def test_no_found_suitable_truck_command(self):
        app_data = Mock()
        auth = Mock()
        app_data.find_route.return_value = Mock()
        app_data.find_suitable_trucks_for_route.return_value = []

        result = FindSuitableTrucksForRoute(["777"], app_data, auth).execute()
        self.assertEqual(result, "No suitable trucks found.")

