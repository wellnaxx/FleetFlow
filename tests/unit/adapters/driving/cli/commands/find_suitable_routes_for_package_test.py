"""Tests for the query-bus-backed suitable-route CLI adapter."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackage,
)
from src.application.queries.routes.find_suitable_routes_for_package import (
    FIND_SUITABLE_ROUTES_FOR_PACKAGE,
    FindSuitableRoutesForPackageQuery,
)
from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage
from src.domain.value_objects.location_code import LocationCode
from src.ports.input.query_bus import QueryBus


class FindSuitableRoutesForPackageShould(unittest.TestCase):
    """Verify package-id parsing, query dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)

    def make_command(self, params: tuple[str, ...]) -> FindSuitableRoutesForPackage:
        """Build the adapter with raw parameters and the mocked bus."""
        return FindSuitableRoutesForPackage(params, self.query_bus)

    def test_dispatches_query_and_formats_mixed_matches(self) -> None:
        self.query_bus.dispatch.return_value = [
            SuitableRouteForPackage(
                route_id=10,
                start_location=LocationCode("SYD"),
                end_location=LocationCode("MEL"),
                eta=datetime(2025, 10, 12, 6, 0),
                capacity_left=123.456,
                end_city=LocationCode("MEL"),
            ),
            SuitableRouteForPackage(
                route_id=11,
                start_location=LocationCode("SYD"),
                end_location=LocationCode("MEL"),
                eta=None,
                capacity_left=None,
                end_city=LocationCode("MEL"),
            ),
        ]

        result = self.make_command(("77",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_ROUTES_FOR_PACKAGE,
            query=FindSuitableRoutesForPackageQuery(package_id=77),
        )
        self.assertEqual(
            result.splitlines(),
            [
                "Route 10: SYD -> MEL, ETA to MEL: 2025-10-12 06:00, Capacity left: 123.46kg",
                "Route 11: SYD -> MEL, ETA to MEL: N/A, Capacity left: No truck",
            ],
        )

    def test_returns_friendly_message_when_no_routes_match(self) -> None:
        self.query_bus.dispatch.return_value = []

        result = self.make_command(("5",)).execute()

        self.assertEqual(result, "No suitable routes found.")
        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_ROUTES_FOR_PACKAGE,
            query=FindSuitableRoutesForPackageQuery(package_id=5),
        )

    def test_rejects_incorrect_parameter_count_without_dispatching(self) -> None:
        with self.assertRaises(ValueError):
            self.make_command(()).execute()

        self.query_bus.dispatch.assert_not_called()

    def test_rejects_invalid_package_id_without_dispatching(self) -> None:
        with self.assertRaisesRegex(ValueError, "package_id"):
            self.make_command(("package",)).execute()

        self.query_bus.dispatch.assert_not_called()

    def test_propagates_permission_error_from_query_bus(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: PACKAGE_FIND_ROUTE_FOR")

        with self.assertRaisesRegex(PermissionError, "PACKAGE_FIND_ROUTE_FOR"):
            self.make_command(("77",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=FIND_SUITABLE_ROUTES_FOR_PACKAGE,
            query=FindSuitableRoutesForPackageQuery(package_id=77),
        )

    def test_propagates_query_bus_failure(self) -> None:
        self.query_bus.dispatch.side_effect = RuntimeError("route search failed")

        with self.assertRaisesRegex(RuntimeError, "route search failed"):
            self.make_command(("77",)).execute()

        self.query_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
