import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.find_suitable_trucks_for_route import FindSuitableTrucksForRoute


class FindSuitableTrucksForRoute_Tests(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> FindSuitableTrucksForRoute:
        cmd = FindSuitableTrucksForRoute.__new__(FindSuitableTrucksForRoute)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(["15"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_FIND_TRUCK_FOR")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_FIND_TRUCK_FOR", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(15)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.try_parse_int")
    def test_success_formats_table(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 15
        cmd = self.make_cmd(["15"])

        trucks = [
            SimpleNamespace(vehicle_id=1, name="Alpha", capacity=10.0, max_range=500, current_location="SYD"),
            SimpleNamespace(vehicle_id=2, name="Bravo", capacity=7.5, max_range=350, current_location="MEL"),
        ]
        cmd._use_case.execute.return_value = trucks  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        mock_validate.assert_called_once_with(("15",), 1)
        mock_parse.assert_called_once_with("15")
        cmd._use_case.execute.assert_called_once_with(15)  # type: ignore[reportUnknownMemberType]

        lines = out.splitlines()
        self.assertEqual(lines[0], "ID | Name   | Capacity | Max Range | Current Location")
        self.assertIn("1 | Alpha | 10.0 kg | 500 km | SYD", lines[1])
        self.assertIn("2 | Bravo | 7.5 kg | 350 km | MEL", lines[2])

    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.try_parse_int")
    def test_no_trucks_returns_friendly_message(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 9
        cmd = self.make_cmd(["9"])
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        mock_validate.assert_called_once_with(("9",), 1)
        mock_parse.assert_called_once_with("9")
        cmd._use_case.execute.assert_called_once_with(9)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(out, "No suitable trucks found.")

    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.try_parse_int")
    def test_missing_route_raises(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 77
        cmd = self.make_cmd(["77"])
        cmd._use_case.execute.side_effect = ValueError("Route with ID 77 not found")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Route with ID 77 not found", str(ctx.exception))
        mock_validate.assert_called_once_with(("77",), 1)
        mock_parse.assert_called_once_with("77")
        cmd._use_case.execute.assert_called_once_with(77)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.try_parse_int")
    def test_parse_failure_bubbles_and_stops(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = ValueError("not an int")
        cmd = self.make_cmd(["x"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not an int", str(ctx.exception))
        mock_validate.assert_called_once_with(("x",), 1)
        mock_parse.assert_called_once_with("x")
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    def test_validate_params_exact_called_with_one(self) -> None:
        cmd = self.make_cmd(["123"])

        with (
            patch(
                "src.adapters.driving.cli.commands.find_suitable_trucks_for_route.validate_params_exact"
            ) as mock_validate,
            patch(
                "src.adapters.driving.cli.commands.find_suitable_trucks_for_route.try_parse_int",
                return_value=123,
            ),
        ):
            cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]
            _ = cmd.execute()
            mock_validate.assert_called_once_with(("123",), 1)

    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_trucks_for_route.try_parse_int")
    def test_downstream_error_propagates(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 5
        cmd = self.make_cmd(["5"])
        cmd._use_case.execute.side_effect = RuntimeError("db failure")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db failure", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(5)  # type: ignore[reportUnknownMemberType]
