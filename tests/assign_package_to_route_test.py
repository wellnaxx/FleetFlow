import unittest
from unittest.mock import MagicMock, call, patch

from adapters.driving.cli.commands.assign_package_to_route import AssignPackageToRoute


class AssignPackageToRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> AssignPackageToRoute:
        cmd = AssignPackageToRoute.__new__(AssignPackageToRoute)
        cmd._params = params  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    @patch("adapters.driving.cli.commands.assign_package_to_route.try_parse_int")
    def test_execute_success_single_package(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["5", "42"])
        cmd._app_data.assign_packages_to_route.return_value = ["assigned package 42 to route 5"]  # type: ignore[reportPrivateUsage]

        result = cmd.execute()

        mock_validate.assert_called_once_with(["5", "42"], 2)
        self.assertEqual(mock_parse.call_count, 2)
        cmd._app_data.assign_packages_to_route.assert_called_once_with(5, [42])  # type: ignore[reportPrivateUsage]
        self.assertEqual(result, "assigned package 42 to route 5")

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    @patch("adapters.driving.cli.commands.assign_package_to_route.try_parse_int")
    def test_execute_success_multiple_packages(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["7", "8", "9", "10"])
        cmd._app_data.assign_packages_to_route.return_value = [  # type: ignore[reportPrivateUsage]
            "assigned 8 to 7",
            "assigned 9 to 7",
            "assigned 10 to 7",
        ]

        # Act
        result = cmd.execute()

        # Assert
        mock_validate.assert_called_once_with(["7", "8", "9", "10"], 2)
        self.assertEqual(mock_parse.call_args_list, [call("7"), call("8"), call("9"), call("10")])
        cmd._app_data.assign_packages_to_route.assert_called_once_with(7, [8, 9, 10])  # type: ignore[reportPrivateUsage]
        self.assertEqual(result, "assigned 8 to 7\nassigned 9 to 7\nassigned 10 to 7")

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    @patch("adapters.driving.cli.commands.assign_package_to_route.try_parse_int")
    def test_execute_returns_empty_string_when_no_messages(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["1", "2"])
        cmd._app_data.assign_packages_to_route.return_value = []  # type: ignore[reportPrivateUsage]

        # Act
        result = cmd.execute()

        # Assert
        self.assertEqual(result, "")

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    def test_execute_raises_when_params_count_invalid(self, mock_validate: MagicMock) -> None:
        # Arrange
        mock_validate.side_effect = ValueError("invalid params count")
        cmd = self.make_cmd(["only_one_param"])

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("invalid params count", str(ctx.exception))
        # Ensure assign is never called (we set it so we can assert)
        self.assertFalse(cmd._app_data.assign_packages_to_route.called)  # type: ignore[reportPrivateUsage]

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    @patch("adapters.driving.cli.commands.assign_package_to_route.try_parse_int")
    def test_execute_raises_when_route_parse_fails(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        # Arrange
        def bad_first_call(v: str) -> int:
            if v == "routeX":
                raise ValueError("not an int")
            return int(v)

        mock_parse.side_effect = bad_first_call
        cmd = self.make_cmd(["routeX", "2"])

        # Act / Assert
        with self.assertRaises(ValueError):
            cmd.execute()
        self.assertFalse(cmd._app_data.assign_packages_to_route.called)  # type: ignore[reportPrivateUsage]

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    @patch("adapters.driving.cli.commands.assign_package_to_route.try_parse_int")
    def test_execute_raises_when_any_package_parse_fails(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        # Arrange: first parse ok (route), second parse fails (first package)
        calls = iter([7, ValueError("bad package id")])

        def side_effect(v: str) -> int:
            val = next(calls)
            if isinstance(val, Exception):
                raise val
            return val

        mock_parse.side_effect = side_effect
        cmd = self.make_cmd(["7", "p1"])

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("bad package id", str(ctx.exception))
        self.assertFalse(cmd._app_data.assign_packages_to_route.called)  # type: ignore[reportPrivateUsage]

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    @patch("adapters.driving.cli.commands.assign_package_to_route.try_parse_int")
    def test_execute_propagates_app_data_errors(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["3", "4"])
        cmd._app_data.assign_packages_to_route.side_effect = ValueError("constraints fail")  # type: ignore[reportPrivateUsage]

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("constraints fail", str(ctx.exception))
        cmd._app_data.assign_packages_to_route.assert_called_once_with(3, [4])  # type: ignore[reportPrivateUsage]

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    @patch("adapters.driving.cli.commands.assign_package_to_route.try_parse_int")
    def test_execute_calls_validate_with_required_min_params(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: int(v)  # type: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
        cmd = self.make_cmd(["1", "2"])

        # Act
        _ = cmd.execute()

        # Assert
        mock_validate.assert_called_once_with(["1", "2"], 2)

    @patch("adapters.driving.cli.commands.assign_package_to_route.validate_params_count")
    @patch("adapters.driving.cli.commands.assign_package_to_route.try_parse_int")
    def test_execute_uses_try_parse_int_for_every_param(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        # Arrange
        mock_parse.side_effect = lambda v: {"10": 10, "20": 20, "30": 30}[v]  # type: ignore[reportUnknownLambdaType]
        cmd = self.make_cmd(["10", "20", "30"])
        cmd._app_data.assign_packages_to_route.return_value = ["ok"]  # type: ignore[reportPrivateUsage]

        # Act
        cmd.execute()

        # Assert
        self.assertEqual(mock_parse.call_args_list, [call("10"), call("20"), call("30")])
        cmd._app_data.assign_packages_to_route.assert_called_once_with(10, [20, 30])  # type: ignore[reportPrivateUsage]
