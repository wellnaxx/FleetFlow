import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.create_route import CreateRoute


class CreateRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> CreateRoute:
        cmd = CreateRoute.__new__(CreateRoute)
        cmd._params = params  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_mutates_state_true(self) -> None:
        self.assertTrue(CreateRoute.mutates_state)

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_success_unscheduled(self, mock_validate: MagicMock, mock_parse: MagicMock) -> None:
        # Arrange
        locs = ["SYD", "MEL", "ADL"]
        mock_parse.return_value = (locs, None)
        cmd = self.make_cmd(["SYD", "MEL", "ADL"])
        route = SimpleNamespace(route_id=42, total_distance_km=1365)
        cmd._app_data.create_route.return_value = route  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        # Assert
        mock_validate.assert_called_once_with(["SYD", "MEL", "ADL"], 2)
        mock_parse.assert_called_once_with(["SYD", "MEL", "ADL"])
        cmd._app_data.create_route.assert_called_once_with(locs, None)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(
            result, "Route 42 created: SYD -> MEL -> ADL | Departure: (unscheduled) | Distance: 1365 km"
        )

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_success_with_departure_datetime(self, mock_validate: MagicMock, mock_parse: MagicMock) -> None:
        # Arrange
        locs = ["SYD", "MEL"]
        departure = datetime(2025, 10, 12, 6, 0)
        mock_parse.return_value = (locs, departure)
        cmd = self.make_cmd(["SYD", "MEL", "2025-10-12", "06:00"])
        route = SimpleNamespace(route_id=7, total_distance_km=878)
        cmd._app_data.create_route.return_value = route  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        # Assert
        mock_validate.assert_called_once_with(["SYD", "MEL", "2025-10-12", "06:00"], 2)
        mock_parse.assert_called_once()
        cmd._app_data.create_route.assert_called_once_with(locs, departure)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Route 7 created: SYD -> MEL | Departure: 2025-10-12 06:00 | Distance: 878 km")

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_message_joins_locations_correctly(self, mock_validate: MagicMock, mock_parse: MagicMock) -> None:
        # Arrange: ensure join uses ' -> '
        locs = ["A", "B", "C", "D"]
        mock_parse.return_value = (locs, None)
        cmd = self.make_cmd(locs)
        cmd._app_data.create_route.return_value = SimpleNamespace(route_id=1, total_distance_km=10)  # type: ignore[reportAttributeAccessIssue]

        # Act
        msg = cmd.execute()

        # Assert
        self.assertIn("A -> B -> C -> D", msg)

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    def test_param_count_error_bubbles_and_stops(self, mock_parse: MagicMock) -> None:
        # Arrange: validate_params_count raises
        cmd = self.make_cmd(["ONLYONE"])
        with (
            patch(
                "src.adapters.driving.cli.commands.create_route.validate_params_count",
                side_effect=ValueError("need at least 2"),
            ),
            self.assertRaises(ValueError) as ctx,
        ):
            cmd.execute()
        self.assertIn("need at least 2", str(ctx.exception))
        mock_parse.assert_not_called()
        cmd._app_data.create_route.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_parse_result_is_passed_verbatim_to_app(
        self, mock_validate: MagicMock, mock_parse: MagicMock
    ) -> None:
        # Arrange: confirm no extra mutation happens to locs/departure
        loc_tokens = ["X1", "Y2"]
        dep = datetime(2030, 1, 2, 3, 4)
        mock_parse.return_value = (loc_tokens, dep)
        cmd = self.make_cmd(["X1", "Y2", "2030-01-02", "03:04"])
        cmd._app_data.create_route.return_value = SimpleNamespace(route_id=9, total_distance_km=123)  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        # Assert
        called_locs, called_dep = cmd._app_data.create_route.call_args[0]  # type: ignore[reportUnknownMemberType]
        self.assertEqual(called_locs, loc_tokens)
        self.assertEqual(called_dep, dep)

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_downstream_error_propagates(self, mock_validate: MagicMock, mock_parse: MagicMock) -> None:
        mock_parse.return_value = (["SYD", "MEL"], None)
        cmd = self.make_cmd(["SYD", "MEL"])
        cmd._app_data.create_route.side_effect = RuntimeError("db failure")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()
        self.assertIn("db failure", str(ctx.exception))
