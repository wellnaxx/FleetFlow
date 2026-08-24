"""Tests for the query-bus-backed suitable-truck CLI adapter."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.find_suitable_trucks_for_route import (
    FindSuitableTrucksForRoute,
)
from src.application.queries.routes.find_suitable_trucks_for_route import (
    FIND_SUITABLE_TRUCKS_FOR_ROUTE,
    FindSuitableTrucksForRouteQuery,
)
from src.ports.input.query_bus import QueryBus


class FindSuitableTrucksForRouteShould(unittest.TestCase):
    """Verify route-id parsing, query dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)

    def make_command(self, params: tuple[str, ...]) -> FindSuitableTrucksForRoute:
        """Build the adapter with raw parameters and the mocked bus."""
        return FindSuitableTrucksForRoute(params, self.query_bus)

    def test_dispatches_query_and_formats_truck_table(self) -> None:
        self.query_bus.dispatch.return_value = [
            SimpleNamespace(
                vehicle_id=1,
                name="Alpha",
                capacity=10.0,
                max_range=500,
                current_location="SYD",
            ),
            SimpleNamespace(
                vehicle_id=2,
                name="Bravo",
                capacity=7.5,
                max_range=350,
                current_location="MEL",
            ),
        ]

        result = self.make_command(("15",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
            query=FindSuitableTrucksForRouteQuery(route_id=15),
        )
        self.assertEqual(
            result.splitlines(),
            [
                "ID | Name   | Capacity | Max Range | Current Location",
                "1 | Alpha | 10.0 kg | 500 km | SYD",
                "2 | Bravo | 7.5 kg | 350 km | MEL",
            ],
        )

    def test_returns_friendly_message_when_no_trucks_match(self) -> None:
        self.query_bus.dispatch.return_value = []

        result = self.make_command(("9",)).execute()

        self.assertEqual(result, "No suitable trucks found.")
        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
            query=FindSuitableTrucksForRouteQuery(route_id=9),
        )

    def test_rejects_incorrect_parameter_count_without_dispatching(self) -> None:
        with self.assertRaises(ValueError):
            self.make_command(()).execute()

        self.query_bus.dispatch.assert_not_called()

    def test_rejects_invalid_route_id_without_dispatching(self) -> None:
        with self.assertRaisesRegex(ValueError, "route_id"):
            self.make_command(("route",)).execute()

        self.query_bus.dispatch.assert_not_called()

    def test_propagates_permission_error_from_query_bus(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_FIND_TRUCK_FOR")

        with self.assertRaisesRegex(PermissionError, "ROUTE_FIND_TRUCK_FOR"):
            self.make_command(("15",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
            query=FindSuitableTrucksForRouteQuery(route_id=15),
        )

    def test_propagates_query_bus_failure(self) -> None:
        self.query_bus.dispatch.side_effect = RuntimeError("db failure")

        with self.assertRaisesRegex(RuntimeError, "db failure"):
            self.make_command(("15",)).execute()

        self.query_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
