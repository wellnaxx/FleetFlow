import unittest
from unittest.mock import Mock
from src.commands.find_suitable_routes_for_package import FindSuitableRoutesForPackage

class TestFindSuitableRoutesForPackage_Should(unittest.TestCase):
    def test_with_none_param_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            cmd = FindSuitableRoutesForPackage([], app_data, auth).execute()

    def test_str_param_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            cmd = FindSuitableRoutesForPackage(["str"], app_data, auth).execute()

    def test_no_found_package_command(self):
        app_data = Mock()
        app_data.view_package.return_value = None
        auth = Mock()
        with self.assertRaises(ValueError):
            cmd = FindSuitableRoutesForPackage(["777"], app_data, auth).execute()

    def test_no_found_route_for_package_command(self):
        app_data = Mock()
        auth = Mock()
        package = Mock()
        package.end_location = "MEL"
        app_data.view_package.return_value = package
        app_data.find_suitable_routes_for_package.return_value = []

        result = FindSuitableRoutesForPackage(["777"], app_data, auth).execute()
        self.assertEqual(result, "No suitable routes found.")





