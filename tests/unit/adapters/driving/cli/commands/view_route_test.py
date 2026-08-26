"""Tests for the query-bus-backed route-detail CLI adapter."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_route import ViewRoute
from src.application.exceptions.application_errors import NotFoundError
from src.application.queries.routes.view_route import VIEW_ROUTE, ViewRouteQuery
from src.ports.input.query_bus import QueryBus


class ViewRouteShould(unittest.TestCase):
    """Verify route-id parsing, query dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)

    def make_command(self, params: tuple[str, ...]) -> ViewRoute:
        """Build the adapter with raw parameters and the mocked bus."""
        return ViewRoute(params, self.query_bus)

    def test_has_no_state_mutation_flags(self) -> None:
        self.assertFalse(getattr(ViewRoute, "mutates_state", False))
        self.assertFalse(getattr(ViewRoute, "mutates_session", False))

    @patch(
        "src.adapters.driving.cli.commands.view_route.render_route_info",
        return_value="ROUTE-INFO",
    )
    def test_dispatches_query_and_renders_route(self, render_route: MagicMock) -> None:
        route = MagicMock()
        self.query_bus.dispatch.return_value = route

        result = self.make_command(("12",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTE,
            query=ViewRouteQuery(route_id=12),
        )
        render_route.assert_called_once_with(route)
        self.assertEqual(result, "ROUTE-INFO")

    def test_rejects_incorrect_parameter_count_without_dispatching(self) -> None:
        with self.assertRaises(ValueError):
            self.make_command(()).execute()

        self.query_bus.dispatch.assert_not_called()

    def test_rejects_invalid_route_id_without_dispatching(self) -> None:
        with self.assertRaisesRegex(ValueError, "route_id"):
            self.make_command(("route",)).execute()

        self.query_bus.dispatch.assert_not_called()

    def test_propagates_permission_error_from_query_bus(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: ROUTE_VIEW")

        with self.assertRaisesRegex(PermissionError, "ROUTE_VIEW"):
            self.make_command(("12",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTE,
            query=ViewRouteQuery(route_id=12),
        )

    def test_propagates_missing_route_error(self) -> None:
        self.query_bus.dispatch.side_effect = NotFoundError("Route with ID 77 not found")

        with self.assertRaisesRegex(NotFoundError, "Route with ID 77 not found"):
            self.make_command(("77",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTE,
            query=ViewRouteQuery(route_id=77),
        )

    def test_propagates_query_bus_failure(self) -> None:
        self.query_bus.dispatch.side_effect = RuntimeError("db down")

        with self.assertRaisesRegex(RuntimeError, "db down"):
            self.make_command(("12",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTE,
            query=ViewRouteQuery(route_id=12),
        )


if __name__ == "__main__":
    unittest.main()
