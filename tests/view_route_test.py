import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from src.commands.view_routes_in_progress import ViewRoutesInProgress


class TestViewRoutesInProgress_Should(unittest.TestCase):

    def setUp(self):
        self.mock_app_data = Mock()
        self.command = ViewRoutesInProgress(params={}, app_data=self.mock_app_data, auth=None)

    def test_no_routes_in_progress(self):
        with patch('src.commands.view_routes_in_progress.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
            self.mock_app_data.view_routes_in_progress.return_value = []

            result = self.command.execute()
            self.assertEqual(result, "No routes in progress.")
            self.mock_app_data.view_routes_in_progress.assert_called_once_with(now=mock_datetime.now())

    def test_routes_in_transit(self):
        mock_route = Mock()
        mock_route.info.return_value = "Route 123 Info"

        mock_pos = Mock()
        mock_pos.kind = "IN_TRANSIT"
        mock_pos.from_city = "City A"
        mock_pos.to_city = "City B"
        mock_pos.next_eta = "14:00"

        with patch('src.commands.view_routes_in_progress.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
            self.mock_app_data.view_routes_in_progress.return_value = [(mock_route, mock_pos)]

            expected_output = "Route 123 Info\n  >> Currently between City A → City B, ETA 14:00\n"
            result = self.command.execute()
            self.assertEqual(result, expected_output)

    def test_routes_at_stop(self):
        mock_route = Mock()
        mock_route.info.return_value = "Route 456 Info"

        mock_pos = Mock()
        mock_pos.kind = "AT_STOP"
        mock_pos.stop_city = "City C"

        with patch('src.commands.view_routes_in_progress.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
            self.mock_app_data.view_routes_in_progress.return_value = [(mock_route, mock_pos)]

            expected_output = "Route 456 Info\n  >> Currently at stop: City C\n"