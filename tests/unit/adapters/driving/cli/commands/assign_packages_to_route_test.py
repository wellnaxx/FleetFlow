import unittest
from typing import cast
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.assign_packages_to_route import AssignPackagesToRoute
from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)


def _parse_int(value: str, _field_name: str = "value") -> int:
    return int(value)


def _collector_mock(command: AssignPackagesToRoute) -> MagicMock:
    """Return the command's injected collector as its test-double type."""
    return cast(MagicMock, command._event_collector)  # pyright: ignore[reportPrivateUsage]


def _use_case_mock(command: AssignPackagesToRoute) -> MagicMock:
    """Return the command's injected use case as its test-double type."""
    return cast(MagicMock, command._use_case)  # pyright: ignore[reportPrivateUsage]


class AssignPackageToRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> AssignPackagesToRoute:
        cmd = AssignPackagesToRoute.__new__(AssignPackagesToRoute)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(["5", "42"])
        _use_case_mock(cmd).execute.side_effect = PermissionError(
            "Missing permission: ROUTE_ASSIGN_PACKAGE"
        )

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_ASSIGN_PACKAGE", str(ctx.exception))
        _use_case_mock(cmd).execute.assert_called_once_with(5, [42])
        _collector_mock(cmd).drain.assert_called_once_with((_use_case_mock(cmd),))

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_success_single_package(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["5", "42"])
        route = MagicMock()
        _use_case_mock(cmd).execute.return_value = AssignPackagesToRouteResult(
            successes=[
                PackageAssignmentSuccess(
                    package_id=42,
                    route_id=5,
                    eta_text="N/A (route unscheduled)",
                    route=route,
                )
            ],
            errors=[],
        )

        result = cmd.execute()

        mock_validate.assert_called_once_with(("5", "42"), 2)
        self.assertEqual(mock_parse.call_args_list, [call("5", "route_id"), call("42", "package_id")])
        _use_case_mock(cmd).execute.assert_called_once_with(5, [42])
        self.assertEqual(
            _collector_mock(cmd).drain.call_args_list,
            [call((_use_case_mock(cmd),)), call((route,))],
        )
        self.assertEqual(result, "Assigned package 42 to route 5. ETA: N/A (route unscheduled)")

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_success_multiple_packages(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["7", "8", "9", "10"])
        route = MagicMock()
        _use_case_mock(cmd).execute.return_value = AssignPackagesToRouteResult(
            successes=[
                PackageAssignmentSuccess(
                    package_id=8, route_id=7, eta_text="2025-10-01 18:00", route=route
                ),
                PackageAssignmentSuccess(
                    package_id=9, route_id=7, eta_text="2025-10-01 19:00", route=route
                ),
                PackageAssignmentSuccess(package_id=10, route_id=7, eta_text="N/A", route=route),
            ],
            errors=[],
        )

        result = cmd.execute()

        mock_validate.assert_called_once_with(("7", "8", "9", "10"), 2)
        self.assertEqual(
            mock_parse.call_args_list,
            [call("7", "route_id"), call("8", "package_id"), call("9", "package_id"), call("10", "package_id")],
        )
        _use_case_mock(cmd).execute.assert_called_once_with(7, [8, 9, 10])
        self.assertEqual(
            _collector_mock(cmd).drain.call_args_list,
            [call((_use_case_mock(cmd),)), call((route,))],
        )
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
        route = MagicMock()
        _use_case_mock(cmd).execute.return_value = AssignPackagesToRouteResult(
            successes=[
                PackageAssignmentSuccess(
                    package_id=8, route_id=7, eta_text="2025-10-01 18:00", route=route
                ),
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
        self.assertEqual(
            _collector_mock(cmd).drain.call_args_list,
            [call((_use_case_mock(cmd),)), call((route,))],
        )

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_drains_only_use_case_when_all_assignments_fail(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["7", "8"])
        _use_case_mock(cmd).execute.return_value = AssignPackagesToRouteResult(
            successes=[],
            errors=[PackageAssignmentError(package_id=8, message="Package 8 not found.")],
        )

        result = cmd.execute()

        self.assertEqual(result, "Failed:\n- Package 8 not found.")
        _collector_mock(cmd).drain.assert_called_once_with((_use_case_mock(cmd),))

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_returns_empty_string_when_result_has_no_messages(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["1", "2"])
        _use_case_mock(cmd).execute.return_value = AssignPackagesToRouteResult(
            successes=[],
            errors=[],
        )

        result = cmd.execute()

        self.assertEqual(result, "")
        _collector_mock(cmd).drain.assert_called_once_with((_use_case_mock(cmd),))

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    def test_execute_raises_when_params_count_invalid(self, mock_validate: MagicMock) -> None:
        mock_validate.side_effect = ValueError("invalid params count")
        cmd = self.make_cmd(["only_one_param"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("invalid params count", str(ctx.exception))
        _use_case_mock(cmd).execute.assert_not_called()

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
        mock_parse.assert_called_once_with("routeX", "route_id")
        _use_case_mock(cmd).execute.assert_not_called()

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
        self.assertEqual(mock_parse.call_args_list, [call("7", "route_id"), call("p1", "package_id")])
        _use_case_mock(cmd).execute.assert_not_called()

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_propagates_use_case_errors(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["3", "4"])
        _use_case_mock(cmd).execute.side_effect = ValueError("constraints fail")

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("constraints fail", str(ctx.exception))
        _use_case_mock(cmd).execute.assert_called_once_with(3, [4])
        _collector_mock(cmd).drain.assert_called_once_with((_use_case_mock(cmd),))

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_propagates_use_case_event_publication_failure_before_route_drain(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["5", "42"])
        route = MagicMock()
        _use_case_mock(cmd).execute.return_value = AssignPackagesToRouteResult(
            successes=[
                PackageAssignmentSuccess(
                    package_id=42,
                    route_id=5,
                    eta_text="N/A",
                    route=route,
                )
            ],
            errors=[],
        )
        _collector_mock(cmd).drain.side_effect = RuntimeError("publisher failed")

        with self.assertRaisesRegex(RuntimeError, "publisher failed"):
            cmd.execute()

        _collector_mock(cmd).drain.assert_called_once_with((_use_case_mock(cmd),))

    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.validate_params_count")
    @patch("src.adapters.driving.cli.commands.assign_packages_to_route.try_parse_int")
    def test_execute_calls_validate_with_required_min_params(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse.side_effect = _parse_int
        cmd = self.make_cmd(["1", "2"])
        _use_case_mock(cmd).execute.return_value = AssignPackagesToRouteResult(
            successes=[], errors=[]
        )

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
        _use_case_mock(cmd).execute.return_value = AssignPackagesToRouteResult(
            successes=[], errors=[]
        )

        cmd.execute()

        self.assertEqual(
            mock_parse.call_args_list,
            [call("10", "route_id"), call("20", "package_id"), call("30", "package_id")],
        )
        _use_case_mock(cmd).execute.assert_called_once_with(10, [20, 30])
