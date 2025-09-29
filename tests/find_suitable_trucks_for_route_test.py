import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

# Adjust import path if your module name differs
from src.commands.find_suitable_trucks_for_route import FindSuitableTrucksForRoute


class FindSuitableTrucksForRoute_Tests(unittest.TestCase):
    def make_cmd(self, params):
        cmd = FindSuitableTrucksForRoute.__new__(FindSuitableTrucksForRoute)
        cmd._params = params
        cmd._app_data = MagicMock()
        return cmd


    @patch('src.commands.find_suitable_trucks_for_route.validate_params_exact')
    @patch('src.commands.find_suitable_trucks_for_route.try_parse_int')
    def test_success_formats_table(self, mock_parse, mock_validate):
        mock_parse.return_value = 15
        cmd = self.make_cmd(["15"])
        # route exists
        cmd._app_data.find_route.return_value = SimpleNamespace(route_id=15)

        trucks = [
            SimpleNamespace(vehicle_id=1, name="Alpha", capacity=10.0, max_range=500, current_location="SYD"),
            SimpleNamespace(vehicle_id=2, name="Bravo", capacity=7.5,  max_range=350, current_location="MEL"),
        ]
        cmd._app_data.find_suitable_trucks_for_route.return_value = trucks

        out = cmd.execute()

        mock_validate.assert_called_once_with(["15"], 1)
        mock_parse.assert_called_once_with("15")
        cmd._app_data.find_route.assert_called_once_with(15)
        cmd._app_data.find_suitable_trucks_for_route.assert_called_once_with(15)

        lines = out.splitlines()
        self.assertEqual(lines[0], "ID | Name   | Capacity | Max Range | Current Location")
        self.assertIn("1 | Alpha | 10.0 kg | 500 km | SYD", lines[1])
        self.assertIn("2 | Bravo | 7.5 kg | 350 km | MEL", lines[2])


    @patch('src.commands.find_suitable_trucks_for_route.validate_params_exact')
    @patch('src.commands.find_suitable_trucks_for_route.try_parse_int')
    def test_no_trucks_returns_friendly_message(self, mock_parse, mock_validate):
        mock_parse.return_value = 9
        cmd = self.make_cmd(["9"])
        cmd._app_data.find_route.return_value = SimpleNamespace(route_id=9)
        cmd._app_data.find_suitable_trucks_for_route.return_value = []

        out = cmd.execute()
        self.assertEqual(out, "No suitable trucks found.")


    @patch('src.commands.find_suitable_trucks_for_route.validate_params_exact')
    @patch('src.commands.find_suitable_trucks_for_route.try_parse_int')
    def test_missing_route_raises(self, mock_parse, mock_validate):
        mock_parse.return_value = 77
        cmd = self.make_cmd(["77"])
        cmd._app_data.find_route.return_value = None

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Route with ID 77 not found", str(ctx.exception))
        cmd._app_data.find_suitable_trucks_for_route.assert_not_called()


    @patch('src.commands.find_suitable_trucks_for_route.validate_params_exact')
    @patch('src.commands.find_suitable_trucks_for_route.try_parse_int')
    def test_parse_failure_bubbles_and_stops(self, mock_parse, mock_validate):
        mock_parse.side_effect = ValueError("not an int")
        cmd = self.make_cmd(["x"])
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("not an int", str(ctx.exception))
        cmd._app_data.find_route.assert_not_called()
        cmd._app_data.find_suitable_trucks_for_route.assert_not_called()

    def test_validate_params_exact_called_with_one(self):
        cmd = self.make_cmd(["123"])
        with patch('src.commands.find_suitable_trucks_for_route.validate_params_exact') as mock_validate, \
             patch('src.commands.find_suitable_trucks_for_route.try_parse_int', return_value=123), \
             patch.object(cmd._app_data, 'find_route', return_value=SimpleNamespace(route_id=123)), \
             patch.object(cmd._app_data, 'find_suitable_trucks_for_route', return_value=[]):
            _ = cmd.execute()
            mock_validate.assert_called_once_with(["123"], 1)


    @patch('src.commands.find_suitable_trucks_for_route.validate_params_exact')
    @patch('src.commands.find_suitable_trucks_for_route.try_parse_int')
    def test_downstream_error_propagates(self, mock_parse, mock_validate):
        mock_parse.return_value = 5
        cmd = self.make_cmd(["5"])
        cmd._app_data.find_route.return_value = SimpleNamespace(route_id=5)
        cmd._app_data.find_suitable_trucks_for_route.side_effect = RuntimeError("db failure")

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()
        self.assertIn("db failure", str(ctx.exception))


    def test_raw_trucks_defaults_to_empty(self):
        cmd = self.make_cmd(["1"])
        self.assertEqual(cmd.raw_trucks, [])

    def test_raw_trucks_returns_internal_list_when_set(self):
        cmd = self.make_cmd(["1"])
        trucks = [SimpleNamespace(vehicle_id=1)]
        cmd._raw_suitable_trucks = trucks
        self.assertIs(cmd.raw_trucks, trucks)

