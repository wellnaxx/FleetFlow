import unittest
from unittest.mock import Mock

from src.commands.remove_route import RemoveRoute


class TestRemoveRoute_Should(unittest.TestCase):
    def test_no_params_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            RemoveRoute([], app_data, auth).execute()

    def test_str_params_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            RemoveRoute(["str"], app_data, auth).execute()

    def test_removed_route_command(self):
        app_data = Mock()
        auth = Mock()
        app_data.remove_route = Mock()

        result = RemoveRoute(["42"], app_data, auth).execute()
        self.assertEqual(result, "Route 42 removed.")