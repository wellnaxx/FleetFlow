"""Tests for the command-bus-backed route package-assignment adapter."""

import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.assign_packages_to_route import AssignPackagesToRoute
from src.application.commands.routes.assign_packages_to_route import (
    ASSIGN_PACKAGES_TO_ROUTE,
    AssignPackagesToRouteCommand,
)
from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)
from src.ports.input.command_bus import CommandBus


class AssignPackagesToRouteShould(unittest.TestCase):
    """Verify parsing, typed dispatch, result rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated command bus for each test."""
        self.command_bus = MagicMock(spec=CommandBus)

    def make_command(self, params: tuple[str, ...]) -> AssignPackagesToRoute:
        """Build the adapter with raw parameters and the mocked bus."""
        return AssignPackagesToRoute(params, self.command_bus)

    def test_mutates_and_autosaves_state(self) -> None:
        self.assertTrue(AssignPackagesToRoute.mutates_state)
        self.assertTrue(AssignPackagesToRoute.autosaves_state)

    def test_dispatches_assignment_command_and_renders_single_success(self) -> None:
        route = MagicMock()
        self.command_bus.dispatch.return_value = AssignPackagesToRouteResult(
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

        result = self.make_command(("5", "42")).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_PACKAGES_TO_ROUTE,
            command=AssignPackagesToRouteCommand(route_id=5, package_ids=(42,)),
        )
        self.assertEqual(result, "Assigned package 42 to route 5. ETA: N/A (route unscheduled)")

    def test_renders_multiple_successes_and_errors_in_result_order(self) -> None:
        route = MagicMock()
        self.command_bus.dispatch.return_value = AssignPackagesToRouteResult(
            successes=[
                PackageAssignmentSuccess(
                    package_id=8,
                    route_id=7,
                    eta_text="2025-10-01 18:00",
                    route=route,
                ),
                PackageAssignmentSuccess(
                    package_id=9,
                    route_id=7,
                    eta_text="N/A",
                    route=route,
                ),
            ],
            errors=[
                PackageAssignmentError(
                    package_id=10,
                    message="Package 10 not found.",
                )
            ],
        )

        result = self.make_command(("7", "8", "9", "10")).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_PACKAGES_TO_ROUTE,
            command=AssignPackagesToRouteCommand(route_id=7, package_ids=(8, 9, 10)),
        )
        self.assertEqual(
            result,
            "Assigned package 8 to route 7. ETA: 2025-10-01 18:00\n"
            "Assigned package 9 to route 7. ETA: N/A\n\n"
            "Failed:\n- Package 10 not found.",
        )

    def test_renders_only_errors(self) -> None:
        self.command_bus.dispatch.return_value = AssignPackagesToRouteResult(
            successes=[],
            errors=[PackageAssignmentError(package_id=8, message="Package 8 not found.")],
        )

        result = self.make_command(("7", "8")).execute()

        self.assertEqual(result, "Failed:\n- Package 8 not found.")

    def test_returns_empty_text_for_empty_result(self) -> None:
        self.command_bus.dispatch.return_value = AssignPackagesToRouteResult(
            successes=[],
            errors=[],
        )

        result = self.make_command(("7", "8")).execute()

        self.assertEqual(result, "")

    def test_rejects_too_few_arguments_without_dispatching(self) -> None:
        with self.assertRaises(ValueError):
            self.make_command(("7",)).execute()

        self.command_bus.dispatch.assert_not_called()

    def test_rejects_invalid_route_id_without_dispatching(self) -> None:
        with self.assertRaisesRegex(ValueError, "route_id"):
            self.make_command(("route", "8")).execute()

        self.command_bus.dispatch.assert_not_called()

    def test_rejects_invalid_package_id_without_dispatching(self) -> None:
        with self.assertRaisesRegex(ValueError, "package_id"):
            self.make_command(("7", "package")).execute()

        self.command_bus.dispatch.assert_not_called()

    def test_propagates_permission_error_from_command_bus(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_ASSIGN_PACKAGE")

        with self.assertRaisesRegex(PermissionError, "ROUTE_ASSIGN_PACKAGE"):
            self.make_command(("5", "42")).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_PACKAGES_TO_ROUTE,
            command=AssignPackagesToRouteCommand(route_id=5, package_ids=(42,)),
        )

    def test_propagates_command_bus_failure(self) -> None:
        self.command_bus.dispatch.side_effect = RuntimeError("assignment failed")

        with self.assertRaisesRegex(RuntimeError, "assignment failed"):
            self.make_command(("5", "42")).execute()

        self.command_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
