import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from datetime import datetime

from src.commands.find_suitable_routes_for_package import FindSuitableRoutesForPackage


class FindSuitableRoutesForPackage_Should(unittest.TestCase):
    def make_cmd(self, params):
        cmd = FindSuitableRoutesForPackage.__new__(FindSuitableRoutesForPackage)
        cmd._params = params
        cmd._app_data = MagicMock()
        return cmd

    @patch('src.commands.find_suitable_routes_for_package.validate_params_exact')
    @patch('src.commands.find_suitable_routes_for_package.try_parse_int')
    def test_success_mixed_matches_formats_lines(self, mock_parse, mock_validate):
        # Arrange
        mock_parse.return_value = 77
        cmd = self.make_cmd(["77"])
        # Package found
        pkg = SimpleNamespace(
            package_id=77,
            start_location="SYD",
            end_location="MEL"
        )
        cmd._app_data.view_package.return_value = pkg

        # Routes: one with truck+eta+capacity, one without truck and no eta
        route_with_truck = SimpleNamespace(
            route_id=10, start_location="SYD", end_location="MEL", truck=SimpleNamespace()
        )
        route_no_truck = SimpleNamespace(
            route_id=11, start_location="SYD", end_location="MEL", truck=None
        )
        matches = [
            {"route": route_with_truck, "eta": datetime(2025, 10, 12, 6, 0), "capacity_left": 123.456},
            {"route": route_no_truck,  "eta": None,                          "capacity_left": None},
        ]
        cmd._app_data.find_suitable_routes_for_package.return_value = matches

        # Act
        result = cmd.execute()

        # Assert calls
        mock_validate.assert_called_once_with(["77"], 1)
        mock_parse.assert_called_once_with("77")
        cmd._app_data.view_package.assert_called_once_with(77)
        cmd._app_data.find_suitable_routes_for_package.assert_called_once_with(77)

        # Assert formatting
        lines = result.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("Route 10: SYD → MEL, ETA to MEL: 2025-10-12 06:00, Capacity left: 123.46kg", lines[0])
        self.assertIn("Route 11: SYD → MEL, ETA to MEL: N/A, Capacity left: No truck", lines[1])

    @patch('src.commands.find_suitable_routes_for_package.validate_params_exact')
    @patch('src.commands.find_suitable_routes_for_package.try_parse_int')
    def test_no_matches_returns_friendly_message(self, mock_parse, mock_validate):
        mock_parse.return_value = 5
        cmd = self.make_cmd(["5"])
        cmd._app_data.view_package.return_value = SimpleNamespace(end_location="ADL")
        cmd._app_data.find_suitable_routes_for_package.return_value = []

        result = cmd.execute()

        self.assertEqual(result, "No suitable routes found.")

    @patch('src.commands.find_suitable_routes_for_package.validate_params_exact')
    @patch('src.commands.find_suitable_routes_for_package.try_parse_int')
    def test_missing_package_raises(self, mock_parse, mock_validate):
        mock_parse.return_value = 42
        cmd = self.make_cmd(["42"])
        cmd._app_data.view_package.return_value = None  # not found

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Package with ID 42 not found", str(ctx.exception))
        cmd._app_data.find_suitable_routes_for_package.assert_not_called()

    @patch('src.commands.find_suitable_routes_for_package.validate_params_exact')
    @patch('src.commands.find_suitable_routes_for_package.try_parse_int')
    def test_parse_failure_bubbles_and_stops(self, mock_parse, mock_validate):
        mock_parse.side_effect = ValueError("not an int")
        cmd = self.make_cmd(["x"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not an int", str(ctx.exception))
        cmd._app_data.view_package.assert_not_called()
        cmd._app_data.find_suitable_routes_for_package.assert_not_called()

    def test_validate_params_exact_called_with_one(self, _unused_mock=None):
        # Separate test to explicitly check the exact count call
        cmd = self.make_cmd(["123"])
        with patch('src.commands.find_suitable_routes_for_package.validate_params_exact') as mock_validate, \
             patch('src.commands.find_suitable_routes_for_package.try_parse_int', return_value=123), \
             patch.object(cmd._app_data, 'view_package', return_value=SimpleNamespace(end_location="MEL")), \
             patch.object(cmd._app_data, 'find_suitable_routes_for_package', return_value=[]):
            _ = cmd.execute()
            mock_validate.assert_called_once_with(["123"], 1)

    @patch('src.commands.find_suitable_routes_for_package.validate_params_exact')
    @patch('src.commands.find_suitable_routes_for_package.try_parse_int')
    def test_capacity_left_is_formatted_to_two_decimals(self, mock_parse, mock_validate):
        mock_parse.return_value = 9
        cmd = self.make_cmd(["9"])
        cmd._app_data.view_package.return_value = SimpleNamespace(end_location="PER")

        r = SimpleNamespace(route_id=3, start_location="A", end_location="B", truck=SimpleNamespace())
        cmd._app_data.find_suitable_routes_for_package.return_value = [
            {"route": r, "eta": None, "capacity_left": 1.2349}
        ]

        out = cmd.execute()
        self.assertIn("Capacity left: 1.23kg", out)  # Python rounds half-even; 1.2349 -> 1.23

