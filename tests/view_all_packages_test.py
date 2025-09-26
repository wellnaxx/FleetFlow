import unittest
from unittest.mock import Mock

from src.commands.view_all_packages import ViewAllPackages


class TestViewAllPackages(unittest.TestCase):

    def setUp(self):
        self.mock_app_data = Mock()
        self.command = ViewAllPackages(params={}, app_data=self.mock_app_data, auth=None)

    def test_no_packages_available(self):
        self.mock_app_data.view_all_packages.return_value = []
        result = self.command.execute()
        self.assertEqual(result, "No packages.")
        self.mock_app_data.view_all_packages.assert_called_once()

    def test_with_multiple_packages(self):
        mock_package1 = Mock()
        mock_package1.info.return_value = "Package 1 Info"

        mock_package2 = Mock()
        mock_package2.info.return_value = "Package 2 Info"

        self.mock_app_data.view_all_packages.return_value = [mock_package1, mock_package2]

        expected_output = "Package 1 Info\n\nPackage 2 Info"
        result = self.command.execute()
        self.assertEqual(result, expected_output)
        self.mock_app_data.view_all_packages.assert_called_once()