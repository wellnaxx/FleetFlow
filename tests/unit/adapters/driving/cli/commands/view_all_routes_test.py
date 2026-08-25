"""Tests for the query-bus-backed route-listing CLI adapter."""

import unittest
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.view_all_routes import ViewAllRoutes
from src.application.queries.routes.view_all_routes import VIEW_ALL_ROUTES, ViewAllRoutesQuery
from src.application.use_cases.pagination import PageResult
from src.ports.input.query_bus import QueryBus


class ViewAllRoutesShould(unittest.TestCase):
    """Verify query dispatch, route rendering, empty state, and failures."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)

    def make_command(self) -> ViewAllRoutes:
        """Build the adapter with no CLI parameters and the mocked bus."""
        return ViewAllRoutes((), self.query_bus)

    def test_has_no_state_mutation_flags(self) -> None:
        self.assertFalse(getattr(ViewAllRoutes, "mutates_state", False))
        self.assertFalse(getattr(ViewAllRoutes, "mutates_session", False))

    def test_dispatches_default_query_and_returns_empty_state(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(),
            total=None,
            limit=None,
            offset=0,
        )

        result = self.make_command().execute()

        self.assertEqual(result, "No routes available.")
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(),
        )

    @patch("src.adapters.driving.cli.commands.view_all_routes.render_route_info")
    def test_renders_multiple_routes_in_order(self, render_route: MagicMock) -> None:
        route_one = MagicMock()
        route_two = MagicMock()
        render_route.side_effect = ["Route 1 Info", "Route 2 Info"]
        self.query_bus.dispatch.return_value = PageResult(
            items=(route_one, route_two),
            total=None,
            limit=None,
            offset=0,
        )

        result = self.make_command().execute()

        self.assertEqual(result, "Route 1 Info\n\nRoute 2 Info")
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(),
        )
        self.assertEqual(
            render_route.call_args_list,
            [call(route_one), call(route_two)],
        )

    def test_propagates_permission_error_from_query_bus(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_VIEW_ALL")

        with self.assertRaisesRegex(PermissionError, "ROUTE_VIEW_ALL"):
            self.make_command().execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(),
        )

    def test_propagates_query_bus_failure(self) -> None:
        self.query_bus.dispatch.side_effect = RuntimeError("db down")

        with self.assertRaisesRegex(RuntimeError, "db down"):
            self.make_command().execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(),
        )


if __name__ == "__main__":
    unittest.main()
