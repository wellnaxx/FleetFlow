import unittest
from unittest.mock import Mock
from src.commands.remove_package import RemovePackage

class TestRemovePackage_Should(unittest.TestCase):
    def test_no_params_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            RemovePackage([], app_data, auth).execute()

    def test_str_params_command(self):
        app_data = Mock()
        auth = Mock()
        with self.assertRaises(ValueError):
            RemovePackage(["str"], app_data, auth).execute()

    def test_removed_package_command(self):
        app_data = Mock()
        auth = Mock()
        app_data.remove_package = Mock()

        result = RemovePackage(["42"], app_data, auth).execute()
        self.assertEqual(result, "Package 42 removed.")




