import unittest
from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.create_route import CreateRoute


def _collector_mock(command: CreateRoute) -> MagicMock:
    """Return the command's injected collector as its test-double type."""
    return cast(MagicMock, command._event_collector)  # pyright: ignore[reportPrivateUsage]


def _use_case_mock(command: CreateRoute) -> MagicMock:
    """Return the command's injected use case as its test-double type."""
    return cast(MagicMock, command._use_case)  # pyright: ignore[reportPrivateUsage]


class CreateRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> CreateRoute:
        cmd = CreateRoute.__new__(CreateRoute)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_mutates_state_true(self) -> None:
        self.assertTrue(CreateRoute.mutates_state)

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(["SYD", "MEL"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_CREATE")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_CREATE", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(["SYD", "MEL"], None)  # type: ignore[reportUnknownMemberType]
        _collector_mock(cmd).drain.assert_called_once_with((_use_case_mock(cmd),))

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_success_unscheduled(self, mock_validate: MagicMock, mock_parse: MagicMock) -> None:
        locs = ["SYD", "MEL", "ADL"]
        mock_parse.return_value = (locs, None)
        cmd = self.make_cmd(["SYD", "MEL", "ADL"])

        route = SimpleNamespace(route_id=42, total_distance_km=1365)
        cmd._use_case.execute.return_value = route  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(("SYD", "MEL", "ADL"), 2)
        mock_parse.assert_called_once_with(["SYD", "MEL", "ADL"])
        cmd._use_case.execute.assert_called_once_with(locs, None)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(
            result,
            "Route 42 created: SYD -> MEL -> ADL | Departure: (unscheduled) | Distance: 1365 km",
        )
        self.assertEqual(
            _collector_mock(cmd).drain.call_args_list,
            [call((_use_case_mock(cmd),)), call((route,))],
        )

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_success_with_departure_datetime(self, mock_validate: MagicMock, mock_parse: MagicMock) -> None:
        locs = ["SYD", "MEL"]
        departure = datetime(2025, 10, 12, 6, 0)
        mock_parse.return_value = (locs, departure)
        cmd = self.make_cmd(["SYD", "MEL", "2025-10-12", "06:00"])

        route = SimpleNamespace(route_id=7, total_distance_km=878)
        cmd._use_case.execute.return_value = route  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(("SYD", "MEL", "2025-10-12", "06:00"), 2)
        mock_parse.assert_called_once_with(["SYD", "MEL", "2025-10-12", "06:00"])
        cmd._use_case.execute.assert_called_once_with(locs, departure)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(
            result,
            "Route 7 created: SYD -> MEL | Departure: 2025-10-12 06:00 | Distance: 878 km",
        )
        self.assertEqual(
            _collector_mock(cmd).drain.call_args_list,
            [call((_use_case_mock(cmd),)), call((route,))],
        )

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_message_joins_locations_correctly(self, mock_validate: MagicMock, mock_parse: MagicMock) -> None:
        locs = ["A", "B", "C", "D"]
        mock_parse.return_value = (locs, None)
        cmd = self.make_cmd(locs)

        cmd._use_case.execute.return_value = SimpleNamespace(route_id=1, total_distance_km=10)  # type: ignore[reportAttributeAccessIssue]

        msg = cmd.execute()

        self.assertIn("A -> B -> C -> D", msg)

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    def test_param_count_error_bubbles_and_stops(self, mock_parse: MagicMock) -> None:
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
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]
        _collector_mock(cmd).drain.assert_not_called()

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_parse_result_is_passed_verbatim_to_use_case(
        self, mock_validate: MagicMock, mock_parse: MagicMock
    ) -> None:
        loc_tokens = ["X1", "Y2"]
        dep = datetime(2030, 1, 2, 3, 4)
        mock_parse.return_value = (loc_tokens, dep)
        cmd = self.make_cmd(["X1", "Y2", "2030-01-02", "03:04"])

        cmd._use_case.execute.return_value = SimpleNamespace(route_id=9, total_distance_km=123)  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        called_locs, called_dep = cmd._use_case.execute.call_args[0]  # type: ignore[reportUnknownMemberType]
        self.assertEqual(called_locs, loc_tokens)
        self.assertEqual(called_dep, dep)

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_downstream_error_propagates(self, mock_validate: MagicMock, mock_parse: MagicMock) -> None:
        mock_parse.return_value = (["SYD", "MEL"], None)
        cmd = self.make_cmd(["SYD", "MEL"])
        cmd._use_case.execute.side_effect = RuntimeError("db failure")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db failure", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(["SYD", "MEL"], None)  # type: ignore[reportUnknownMemberType]
        _collector_mock(cmd).drain.assert_called_once_with((_use_case_mock(cmd),))

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    @patch("src.adapters.driving.cli.commands.create_route.validate_params_count")
    def test_use_case_event_publication_failure_prevents_route_drain(
        self,
        mock_validate: MagicMock,
        mock_parse: MagicMock,
    ) -> None:
        mock_parse.return_value = (["SYD", "MEL"], None)
        cmd = self.make_cmd(["SYD", "MEL"])
        route = SimpleNamespace(route_id=1, total_distance_km=100)
        cmd._use_case.execute.return_value = route  # type: ignore[reportAttributeAccessIssue]
        _collector_mock(cmd).drain.side_effect = RuntimeError("publisher failed")

        with self.assertRaisesRegex(RuntimeError, "publisher failed"):
            cmd.execute()

        _collector_mock(cmd).drain.assert_called_once_with((_use_case_mock(cmd),))
