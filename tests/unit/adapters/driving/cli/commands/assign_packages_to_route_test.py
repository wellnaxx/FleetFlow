import unittest
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.assign_packages_to_route import AssignPackagesToRoute
from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)


def _parse_int(value: str) -> int:
    return int(value)


class AssignPackageToRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> AssignPackagesToRoute:
        cmd = AssignPackagesToRoute.__new__(AssignPackagesToRoute)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(["5", "42"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_ASSIGN_PACKAGE")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_ASSIGN_PACKAGE", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(5, [42])  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_success_single_package(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["5", "42"])
        cmd._use_case.execute.return_value = AssignPackagesToRouteResult(  # type: ignore[reportAttributeAccessIssue]
            successes=[
                PackageAssignmentSuccess(
                    package_id=42,
                    route_id=5,
                    eta_text="N/A (route unscheduled)",
                )
            ],
            errors=[],
        )

        result = cmd.execute()

        mock_validate.assert_called_once_with(("5", "42"), 2)
        self.assertEqual(mock_parse.call_args_list, [call("5"), call("42")])
        cmd._use_case.execute.assert_called_once_with(5, [42])  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Assigned package 42 to route 5. ETA: N/A (route unscheduled)")

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_success_multiple_packages(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["7", "8", "9", "10"])
        cmd._use_case.execute.return_value = AssignPackagesToRouteResult(  # type: ignore[reportAttributeAccessIssue]
            successes=[
                PackageAssignmentSuccess(package_id=8, route_id=7, eta_text="2025-10-01 18:00"),
                PackageAssignmentSuccess(package_id=9, route_id=7, eta_text="2025-10-01 19:00"),
                PackageAssignmentSuccess(package_id=10, route_id=7, eta_text="N/A"),
            ],
            errors=[],
        )

        result = cmd.execute()

        mock_validate.assert_called_once_with(("7", "8", "9", "10"), 2)
        self.assertEqual(mock_parse.call_args_list, [call("7"), call("8"), call("9"), call("10")])
        cmd._use_case.execute.assert_called_once_with(7, [8, 9, 10])  # type: ignore[reportUnknownMemberType]
        self.assertEqual(
            result,
            "\n".join(
                [
                    "Assigned package 8 to route 7. ETA: 2025-10-01 18:00",
                    "Assigned package 9 to route 7. ETA: 2025-10-01 19:00",
                    "Assigned package 10 to route 7. ETA: N/A",
                ]
            ),
        )

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_formats_successes_and_errors(
        self, mock_parse: MagicMock, mock_validate: MagicMock
    ) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["7", "8", "9"])
        cmd._use_case.execute.return_value = AssignPackagesToRouteResult(  # type: ignore[reportAttributeAccessIssue]
            successes=[
                PackageAssignmentSuccess(package_id=8, route_id=7, eta_text="2025-10-01 18:00"),
            ],
            errors=[
                PackageAssignmentError(
                    package_id=9,
                    message="Package 9 is already on route 2.",
                )
            ],
        )

        result = cmd.execute()

        self.assertEqual(
            result,
            "Assigned package 8 to route 7. ETA: 2025-10-01 18:00\n\n"
            "Failed:\n- Package 9 is already on route 2.",
        )

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_returns_empty_string_when_result_has_no_messages(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["1", "2"])
        cmd._use_case.execute.return_value = AssignPackagesToRouteResult(  # type: ignore[reportAttributeAccessIssue]
            successes=[],
            errors=[],
        )

        result = cmd.execute()

        self.assertEqual(result, "")

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    def test_execute_raises_when_params_count_invalid(self, mock_validate: MagicMock) -> None:
        mock_validate.side_effect = ValueError("invalid params count")
        cmd = self.make_cmd(["only_one_param"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("invalid params count", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_raises_when_route_parse_fails(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = ValueError("not an int")
        cmd = self.make_cmd(["routeX", "2"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not an int", str(ctx.exception))
        mock_validate.assert_called_once_with(("routeX", "2"), 2)
        mock_parse.assert_called_once_with("routeX")
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_raises_when_any_package_parse_fails(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = [7, ValueError("bad package id")]
        cmd = self.make_cmd(["7", "p1"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("bad package id", str(ctx.exception))
        self.assertEqual(mock_parse.call_args_list, [call("7"), call("p1")])
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_propagates_use_case_errors(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["3", "4"])
        cmd._use_case.execute.side_effect = ValueError("constraints fail")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("constraints fail", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(3, [4])  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_calls_validate_with_required_min_params(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["1", "2"])
        cmd._use_case.execute.return_value = AssignPackagesToRouteResult(successes=[], errors=[])  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        mock_validate.assert_called_once_with(("1", "2"), 2)

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_uses_try_parse_int_for_every_param(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = [10, 20, 30]
        cmd = self.make_cmd(["10", "20", "30"])
        cmd._use_case.execute.return_value = AssignPackagesToRouteResult(successes=[], errors=[])  # type: ignore[reportAttributeAccessIssue]

        cmd.execute()

        self.assertEqual(mock_parse.call_args_list, [call("10"), call("20"), call("30")])
        cmd._use_case.execute.assert_called_once_with(10, [20, 30])  # type: ignore[reportUnknownMemberType]
