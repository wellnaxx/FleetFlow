"""Tests for the command-bus-backed truck-assignment CLI adapter."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.assign_truck_to_route import AssignTruckToRoute
from src.application.commands.routes.assign_truck_to_route import (
    ASSIGN_TRUCK_TO_ROUTE,
    AssignTruckToRouteCommand,
)
from src.application.results.assign_truck_to_route_result import AssignTruckToRouteResult
from src.ports.input.command_bus import CommandBus


class AssignTruckToRouteShould(unittest.TestCase):
    """Verify parsing, deterministic command dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated command bus for each test."""
        self.command_bus = MagicMock(spec=CommandBus)

    def make_command(self, params: tuple[str, ...]) -> AssignTruckToRoute:
        """Build the adapter with raw parameters and the mocked bus."""
        return AssignTruckToRoute(params, self.command_bus)

    def test_mutates_and_autosaves_state(self) -> None:
        self.assertTrue(AssignTruckToRoute.mutates_state)
        self.assertTrue(AssignTruckToRoute.autosaves_state)

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    def test_dispatches_timed_assignment_command_and_renders_confirmation(
        self,
        datetime_mock: MagicMock,
    ) -> None:
        now = datetime(2025, 10, 12, 6, 0)
        datetime_mock.now.return_value = now
        route = MagicMock()
        self.command_bus.dispatch.return_value = AssignTruckToRouteResult(
            route_id=22,
            truck_id=11,
            route=route,
        )

        result = self.make_command(("11", "22")).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_TRUCK_TO_ROUTE,
            command=AssignTruckToRouteCommand(truck_id=11, route_id=22, now=now),
        )
        self.assertEqual(result, "Assigned truck 11 to route 22.")

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    def test_confirmation_uses_route_id_returned_by_workflow(self, datetime_mock: MagicMock) -> None:
        datetime_mock.now.return_value = datetime(2025, 10, 12, 6, 0)
        self.command_bus.dispatch.return_value = AssignTruckToRouteResult(
            route_id=999,
            truck_id=5,
            route=MagicMock(),
        )

        result = self.make_command(("5", "7")).execute()

        self.assertEqual(result, "Assigned truck 5 to route 999.")

    def test_rejects_incorrect_parameter_count_without_dispatching(self) -> None:
        with self.assertRaises(ValueError):
            self.make_command(("11",)).execute()

        self.command_bus.dispatch.assert_not_called()

    def test_rejects_invalid_truck_id_without_dispatching(self) -> None:
        with self.assertRaisesRegex(ValueError, "truck_id"):
            self.make_command(("truck", "22")).execute()

        self.command_bus.dispatch.assert_not_called()

    def test_rejects_invalid_route_id_without_dispatching(self) -> None:
        with self.assertRaisesRegex(ValueError, "route_id"):
            self.make_command(("11", "route")).execute()

        self.command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    def test_propagates_permission_error_from_command_bus(self, datetime_mock: MagicMock) -> None:
        now = datetime(2025, 10, 12, 6, 0)
        datetime_mock.now.return_value = now
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_ASSIGN_TRUCK")

        with self.assertRaisesRegex(PermissionError, "ROUTE_ASSIGN_TRUCK"):
            self.make_command(("11", "22")).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=ASSIGN_TRUCK_TO_ROUTE,
            command=AssignTruckToRouteCommand(truck_id=11, route_id=22, now=now),
        )

    @patch("src.adapters.driving.cli.commands.assign_truck_to_route.datetime")
    def test_propagates_command_bus_failure(self, datetime_mock: MagicMock) -> None:
        datetime_mock.now.return_value = datetime(2025, 10, 12, 6, 0)
        self.command_bus.dispatch.side_effect = RuntimeError("assignment failed")

        with self.assertRaisesRegex(RuntimeError, "assignment failed"):
            self.make_command(("11", "22")).execute()

        self.command_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
