"""Tests for the command-bus-backed route-creation CLI adapter."""

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.create_route import CreateRoute
from src.application.commands.routes.create_route import CREATE_ROUTE, CreateRouteCommand
from src.ports.input.command_bus import CommandBus


class CreateRouteShould(unittest.TestCase):
    """Verify route argument parsing, typed dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated command bus for each test."""
        self.command_bus = MagicMock(spec=CommandBus)

    def make_command(self, params: tuple[str, ...]) -> CreateRoute:
        """Build the adapter with raw parameters and the mocked bus."""
        return CreateRoute(params, self.command_bus)

    def test_mutates_and_autosaves_state(self) -> None:
        self.assertTrue(CreateRoute.mutates_state)
        self.assertTrue(CreateRoute.autosaves_state)

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    def test_dispatches_unscheduled_route_command_and_renders_confirmation(
        self,
        parse_departure: MagicMock,
    ) -> None:
        parse_departure.return_value = (["SYD", "MEL", "ADL"], None)
        self.command_bus.dispatch.return_value = SimpleNamespace(
            route_id=42,
            total_distance_km=1365,
        )

        result = self.make_command(("SYD", "MEL", "ADL")).execute()

        parse_departure.assert_called_once_with(["SYD", "MEL", "ADL"])
        self.command_bus.dispatch.assert_called_once_with(
            key=CREATE_ROUTE,
            command=CreateRouteCommand(
                locations=("SYD", "MEL", "ADL"),
                departure_time=None,
            ),
        )
        self.assertEqual(
            result,
            "Route 42 created: SYD -> MEL -> ADL | Departure: (unscheduled) | Distance: 1365 km",
        )

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    def test_dispatches_scheduled_route_command_and_formats_departure(
        self,
        parse_departure: MagicMock,
    ) -> None:
        departure = datetime(2025, 10, 12, 6, 0)
        parse_departure.return_value = (["SYD", "MEL"], departure)
        self.command_bus.dispatch.return_value = SimpleNamespace(
            route_id=7,
            total_distance_km=878,
        )

        result = self.make_command(("SYD", "MEL", "2025-10-12", "06:00")).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=CREATE_ROUTE,
            command=CreateRouteCommand(
                locations=("SYD", "MEL"),
                departure_time=departure,
            ),
        )
        self.assertEqual(
            result,
            "Route 7 created: SYD -> MEL | Departure: 2025-10-12 06:00 | Distance: 878 km",
        )

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    def test_rejects_too_few_arguments_before_parsing_or_dispatch(
        self,
        parse_departure: MagicMock,
    ) -> None:
        with self.assertRaises(ValueError):
            self.make_command(("SYD",)).execute()

        parse_departure.assert_not_called()
        self.command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    def test_propagates_departure_parse_error_without_dispatching(
        self,
        parse_departure: MagicMock,
    ) -> None:
        parse_departure.side_effect = ValueError("Invalid departure time")

        with self.assertRaisesRegex(ValueError, "Invalid departure time"):
            self.make_command(("SYD", "MEL", "invalid")).execute()

        self.command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    def test_propagates_permission_error_from_command_bus(
        self,
        parse_departure: MagicMock,
    ) -> None:
        parse_departure.return_value = (["SYD", "MEL"], None)
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_CREATE")

        with self.assertRaisesRegex(PermissionError, "ROUTE_CREATE"):
            self.make_command(("SYD", "MEL")).execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=CREATE_ROUTE,
            command=CreateRouteCommand(locations=("SYD", "MEL")),
        )

    @patch("src.adapters.driving.cli.commands.create_route.parse_departure_from_tail")
    def test_propagates_command_bus_failure(self, parse_departure: MagicMock) -> None:
        parse_departure.return_value = (["SYD", "MEL"], None)
        self.command_bus.dispatch.side_effect = RuntimeError("route write failed")

        with self.assertRaisesRegex(RuntimeError, "route write failed"):
            self.make_command(("SYD", "MEL")).execute()

        self.command_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
