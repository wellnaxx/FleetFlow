import unittest
from unittest.mock import MagicMock, call, patch

from adapters.driving.cli.commands.assign_truck_to_route import AssignTruckToRoute


class AssignTruckToRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> AssignTruckToRoute:
        """Instantiate without BaseCommand.__init__ and inject minimal attrs used by execute()."""
        cmd = AssignTruckToRoute.__new__(AssignTruckToRoute)
        cmd._params = params  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_mutates_state_true(self) -> None:
        self.assertTrue(AssignTruckToRoute.mutates_state)

    @patch("adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_success(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["11", "22"])
        route_obj = MagicMock()
        route_obj.route_id = 22
        cmd._app_data.assign_truck_to_route.return_value = route_obj  # type: ignore[reportPrivateUsage]

        # Act
        result = cmd.execute()

        # Assert
        mock_validate.assert_called_once_with(["11", "22"], 2)  # type: ignore[reportUnknownMemberType]
        self.assertEqual(mock_parse.call_args_list, [call("11"), call("22")])  # type: ignore[reportUnknownMemberType]
        cmd._app_data.assign_truck_to_route.assert_called_once_with(11, 22)  # type: ignore[reportAttributeAccessIssue]
        self.assertEqual(result, "Assigned truck 11 to route 22.")

    @patch("adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_message_uses_returned_route_id(
        self, mock_parse: MagicMock, mock_validate: MagicMock
    ) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["5", "7"])
        route_obj = MagicMock()
        route_obj.route_id = 999  # ensure message pulls from route.route_id
        cmd._app_data.assign_truck_to_route.return_value = route_obj  # type: ignore[reportPrivateUsage]

        # Act
        result = cmd.execute()

        # Assert
        self.assertEqual(result, "Assigned truck 5 to route 999.")

    @patch("adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    def test_execute_raises_when_param_count_invalid(self, mock_validate: MagicMock) -> None:
        # Arrange
        mock_validate.side_effect = ValueError("expected exactly 2 params")
        cmd = self.make_cmd(["only_one"])

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("expected exactly 2 params", str(ctx.exception))
        # ensure downstream not called
        self.assertFalse(cmd._app_data.assign_truck_to_route.called)  # type: ignore[reportAttributeAccessIssue]

    @patch("adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_raises_when_truck_id_parse_fails(
        self, mock_parse: MagicMock, mock_validate: MagicMock
    ) -> None:
        # Arrange: first parse (truck) fails
        def side_effect(v: str) -> int:
            if v == "truckX":
                raise ValueError("not an int")
            return int(v)

        mock_parse.side_effect = side_effect
        cmd = self.make_cmd(["truckX", "2"])

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("not an int", str(ctx.exception))
        self.assertFalse(cmd._app_data.assign_truck_to_route.called)  # type: ignore[reportAttributeAccessIssue]

    @patch("adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_raises_when_route_id_parse_fails(
        self, mock_parse: MagicMock, mock_validate: MagicMock
    ) -> None:
        # Arrange: truck ok, route fails
        calls = iter([13, ValueError("bad route id")])

        def parse_seq(_):
            val = next(calls)
            if isinstance(val, Exception):
                raise val
            return val

        mock_parse.side_effect = parse_seq
        cmd = self.make_cmd(["13", "routeY"])

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("bad route id", str(ctx.exception))
        self.assertFalse(cmd._app_data.assign_truck_to_route.called)  # type: ignore[reportAttributeAccessIssue]

    @patch("adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_propagates_app_data_errors(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["3", "4"])
        cmd._app_data.assign_truck_to_route.side_effect = ValueError("precondition failed")  # type: ignore[reportAttributeAccessIssue]

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("precondition failed", str(ctx.exception))
        cmd._app_data.assign_truck_to_route.assert_called_once_with(3, 4)  # type: ignore[reportAttributeAccessIssue]

    @patch("adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_execute_uses_try_parse_int_for_both_params(
        self, mock_parse: MagicMock, mock_validate: MagicMock
    ) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: {"10": 10, "20": 20}[v]  # type: ignore[reportUnknownLambdaType]
        cmd = self.make_cmd(["10", "20"])
        route_obj = MagicMock()
        route_obj.route_id = 20
        cmd._app_data.assign_truck_to_route.return_value = route_obj  # type: ignore[reportPrivateUsage]

        # Act
        _ = cmd.execute()

        # Assert
        self.assertEqual(mock_parse.call_args_list, [call("10"), call("20")])  # type: ignore[reportUnknownMemberType]
        cmd._app_data.assign_truck_to_route.assert_called_once_with(10, 20)  # type: ignore[reportAttributeAccessIssue]

    @patch("adapters.driving.cli.commands.assign_truck_to_route.validate_params_exact")
    @patch("adapters.driving.cli.commands.assign_truck_to_route.try_parse_int")
    def test_validate_called_with_exact_two(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["1", "2"])
        route_obj = MagicMock()
        route_obj.route_id = 2
        cmd._app_data.assign_truck_to_route.return_value = route_obj  # type: ignore[reportPrivateUsage]

        # Act
        _ = cmd.execute()

        # Assert
        mock_validate.assert_called_once_with(["1", "2"], 2)  # type: ignore[reportUnknownMemberType]
