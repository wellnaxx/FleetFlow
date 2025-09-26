import unittest
from unittest.mock import Mock

from src.commands.view_all_routes import ViewAllRoutes


class TestViewAllRoutes_Should(unittest.TestCase):

    def setUp(self):
        self.mock_app_data = Mock()
        self.command = ViewAllRoutes(params={}, app_data=self.mock_app_data, auth=None)

    def test_no_routes_available(self):
        self.mock_app_data.view_all_routes.return_value = []
        result = self.command.execute()
        self.assertEqual(result, "No routes available.")
        self.mock_app_data.view_all_routes.assert_called_once()

    def test_with_multiple_routes(self):
        mock_route1 = Mock()
        mock_route1.info.return_value = "Route 1 Info"

        mock_route2 = Mock()
        mock_route2.info.return_value = "Route 2 Info"

        self.mock_app_data.view_all_routes.return_value = [mock_route1, mock_route2]

        expected_output = "Route 1 Info\n\nRoute 2 Info"
        result = self.command.execute()
        self.assertEqual(result, expected_output)
        self.mock_app_data.view_all_routes.assert_called_once()
