"""Tests for the query-bus-backed active-route CLI adapter."""

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress
from src.application.queries.routes.view_routes_in_progress import (
    VIEW_ROUTES_IN_PROGRESS,
    ViewRoutesInProgressQuery,
)
from src.domain.entities.delivery_route import RoutePositionKind
from src.ports.input.query_bus import QueryBus

NOW = datetime(2025, 9, 27, 11, 30)


class ViewRoutesInProgressShould(unittest.TestCase):
    """Verify active-route dispatch, rendering, empty state, and failures."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)

    def make_command(self) -> ViewRoutesInProgress:
        """Build the adapter with no CLI parameters and the mocked bus."""
        return ViewRoutesInProgress((), self.query_bus)

    def assert_dispatched_current_query(self) -> None:
        """Assert dispatch used the canonical key and fixed business time."""
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ROUTES_IN_PROGRESS,
            query=ViewRoutesInProgressQuery(now=NOW),
        )

    def test_has_no_state_mutation_flags(self) -> None:
        self.assertFalse(getattr(ViewRoutesInProgress, "mutates_state", False))
        self.assertFalse(getattr(ViewRoutesInProgress, "mutates_session", False))

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_returns_empty_state_when_no_routes_are_active(self, datetime_mock: MagicMock) -> None:
        datetime_mock.now.return_value = NOW
        self.query_bus.dispatch.return_value = []

        result = self.make_command().execute()

        self.assertEqual(result, "No routes in progress.")
        self.assert_dispatched_current_query()

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.render_route_info")
    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_renders_in_transit_and_at_stop_routes(
        self,
        datetime_mock: MagicMock,
        render_route: MagicMock,
    ) -> None:
        datetime_mock.now.return_value = NOW
        route_one = MagicMock()
        route_two = MagicMock()
        in_transit = SimpleNamespace(
            kind=RoutePositionKind.IN_TRANSIT,
            from_city="SYD",
            to_city="MEL",
            next_eta="2025-10-12 06:00",
        )
        at_stop = SimpleNamespace(kind=RoutePositionKind.AT_STOP, stop_city="MEL")
        self.query_bus.dispatch.return_value = [
            (route_one, in_transit),
            (route_two, at_stop),
        ]
        render_route.side_effect = ["Route 7: SYD -> MEL", "Route 9: MEL -> ADL"]

        result = self.make_command().execute()

        self.assertEqual(
            result.split("\n"),
            [
                "Route 7: SYD -> MEL",
                "  >> Currently between SYD -> MEL, ETA 2025-10-12 06:00",
                "",
                "Route 9: MEL -> ADL",
                "  >> Currently at stop: MEL",
                "",
            ],
        )
        self.assert_dispatched_current_query()
        self.assertEqual(
            render_route.call_args_list,
            [call(route_one, position=in_transit), call(route_two, position=at_stop)],
        )

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.render_route_info")
    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_unknown_position_kind_keeps_route_summary(
        self,
        datetime_mock: MagicMock,
        render_route: MagicMock,
    ) -> None:
        datetime_mock.now.return_value = NOW
        route = MagicMock()
        position = SimpleNamespace(kind="SOMETHING_ELSE")
        self.query_bus.dispatch.return_value = [(route, position)]
        render_route.return_value = "Route 1"

        result = self.make_command().execute()

        self.assertEqual(result.split("\n"), ["Route 1", ""])
        render_route.assert_called_once_with(route, position=position)

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_propagates_permission_error_from_query_bus(self, datetime_mock: MagicMock) -> None:
        datetime_mock.now.return_value = NOW
        self.query_bus.dispatch.side_effect = PermissionError(
            "Missing permission: ROUTE_VIEW_IN_PROGRESS"
        )

        with self.assertRaisesRegex(PermissionError, "ROUTE_VIEW_IN_PROGRESS"):
            self.make_command().execute()

        self.assert_dispatched_current_query()

    @patch("src.adapters.driving.cli.commands.view_routes_in_progress.datetime")
    def test_propagates_query_bus_failure(self, datetime_mock: MagicMock) -> None:
        datetime_mock.now.return_value = NOW
        self.query_bus.dispatch.side_effect = RuntimeError("db down")

        with self.assertRaisesRegex(RuntimeError, "db down"):
            self.make_command().execute()

        self.assert_dispatched_current_query()


if __name__ == "__main__":
    unittest.main()
