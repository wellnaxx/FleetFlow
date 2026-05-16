import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.assign_truck_to_route import AssignTruckToRoute


class AssignTruckToRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> AssignTruckToRoute:
        cmd = AssignTruckToRoute.__new__(AssignTruckToRoute)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_mutates_state_true(self) -> None:
        self.assertTrue(AssignTruckToRoute.mutates_state)

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    def test_execute_propagates_permission_errors_from_use_case(self, mock_dt: MagicMock) -> None:
        fixed_now = datetime(2025, 10, 12, 6, 0)
        mock_dt.now.return_value = fixed_now
        cmd = self.make_cmd(["11", "22"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_ASSIGN_TRUCK")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_ASSIGN_TRUCK", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(11, 22, fixed_now)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_success(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
        mock_dt: MagicMock,
    ) -> None:
        fixed_now = datetime(2025, 10, 12, 6, 0)
        mock_dt.now.return_value = fixed_now
        mock_parse.side_effect = [11, 22]

        cmd = self.make_cmd(["11", "22"])
        cmd._use_case.execute.return_value = MagicMock(route_id=22)  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(("11", "22"), 2)
        self.assertEqual(mock_parse.call_args_list, [call("11"), call("22")])
        cmd._use_case.execute.assert_called_once_with(11, 22, fixed_now)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Assigned truck 11 to route 22.")

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_message_uses_returned_route_id(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
        mock_dt: MagicMock,
    ) -> None:
        mock_dt.now.return_value = datetime(2025, 10, 12, 6, 0)
        mock_parse.side_effect = [5, 7]

        cmd = self.make_cmd(["5", "7"])
        cmd._use_case.execute.return_value = MagicMock(route_id=999)  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "Assigned truck 5 to route 999.")

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    def test_execute_raises_when_param_count_invalid(self, mock_validate: MagicMock) -> None:
        mock_validate.side_effect = ValueError("expected exactly 2 params")
        cmd = self.make_cmd(["only_one"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("expected exactly 2 params", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_raises_when_truck_id_parse_fails(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = ValueError("not an int")
        cmd = self.make_cmd(["truckX", "2"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not an int", str(ctx.exception))
        mock_validate.assert_called_once_with(("truckX", "2"), 2)
        mock_parse.assert_called_once_with("truckX")
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_raises_when_route_id_parse_fails(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = [13, ValueError("bad route id")]
        cmd = self.make_cmd(["13", "routeY"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("bad route id", str(ctx.exception))
        mock_validate.assert_called_once_with(("13", "routeY"), 2)
        self.assertEqual(mock_parse.call_args_list, [call("13"), call("routeY")])
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_propagates_use_case_errors(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
        mock_dt: MagicMock,
    ) -> None:
        fixed_now = datetime(2025, 10, 12, 6, 0)
        mock_dt.now.return_value = fixed_now
        mock_parse.side_effect = [3, 4]

        cmd = self.make_cmd(["3", "4"])
        cmd._use_case.execute.side_effect = ValueError("precondition failed")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("precondition failed", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(3, 4, fixed_now)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_uses_try_parse_int_for_both_params(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
        mock_dt: MagicMock,
    ) -> None:
        mock_dt.now.return_value = datetime(2025, 10, 12, 6, 0)
        mock_parse.side_effect = [10, 20]

        cmd = self.make_cmd(["10", "20"])
        cmd._use_case.execute.return_value = MagicMock(route_id=20)  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        self.assertEqual(mock_parse.call_args_list, [call("10"), call("20")])
        cmd._use_case.execute.assert_called_once()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_validate_called_with_exact_two(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
        mock_dt: MagicMock,
    ) -> None:
        mock_dt.now.return_value = datetime(2025, 10, 12, 6, 0)
        mock_parse.side_effect = [1, 2]

        cmd = self.make_cmd(["1", "2"])
        cmd._use_case.execute.return_value = MagicMock(route_id=2)  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        mock_validate.assert_called_once_with(("1", "2"), 2)
