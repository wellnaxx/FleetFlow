"""Tests for the command-bus-backed remove-route CLI adapter."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.remove_route import RemoveRoute
from src.application.commands.routes.remove_route import REMOVE_ROUTE, RemoveRouteCommand
from src.ports.input.command_bus import CommandBus


class RemoveRouteShould(unittest.TestCase):
    """Verify route-id parsing, command dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated command bus for each test."""
        self.command_bus = MagicMock(spec=CommandBus)

    def make_command(self, params: tuple[str, ...]) -> RemoveRoute:
        """Build the adapter with raw parameters and the mocked bus."""
        return RemoveRoute(params, self.command_bus)

    def test_mutates_and_autosaves_state(self) -> None:
        self.assertTrue(RemoveRoute.mutates_state)
        self.assertTrue(RemoveRoute.autosaves_state)

    def test_dispatches_remove_command_and_renders_confirmation(self) -> None:
        result = self.make_command(("42",)).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=REMOVE_ROUTE,
            command=RemoveRouteCommand(route_id=42),
        )
        self.assertEqual(result, "Route 42 removed.")

    def test_propagates_permission_error_from_command_bus(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_REMOVE")

        with self.assertRaisesRegex(PermissionError, "ROUTE_REMOVE"):
            self.make_command(("42",)).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=REMOVE_ROUTE,
            command=RemoveRouteCommand(route_id=42),
        )

    @patch("src.adapters.driving.cli.commands.remove_route.try_parse_int")
    @patch("src.adapters.driving.cli.commands.remove_route.validate_params_exact")
    def test_parameter_count_failure_prevents_parsing_and_dispatch(
        self,
        validate_params: MagicMock,
        parse_int: MagicMock,
    ) -> None:
        validate_params.side_effect = ValueError("Expected 1 parameter(s).")

        with self.assertRaisesRegex(ValueError, "Expected 1 parameter"):
            self.make_command(()).execute()

        validate_params.assert_called_once_with((), 1)
        parse_int.assert_not_called()
        self.command_bus.dispatch.assert_not_called()

    def test_invalid_route_id_prevents_dispatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "route_id"):
            self.make_command(("route",)).execute()

        self.command_bus.dispatch.assert_not_called()

    def test_propagates_command_bus_failure(self) -> None:
        self.command_bus.dispatch.side_effect = RuntimeError("delete failed")

        with self.assertRaisesRegex(RuntimeError, "delete failed"):
            self.make_command(("42",)).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=REMOVE_ROUTE,
            command=RemoveRouteCommand(route_id=42),
        )


if __name__ == "__main__":
    unittest.main()
