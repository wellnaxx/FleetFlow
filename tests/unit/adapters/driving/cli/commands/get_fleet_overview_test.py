"""Tests for the fleet-overview CLI command."""

import unittest
from typing import cast
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.get_fleet_overview import GetFleetOverview
from src.application.exceptions.application_errors import ValidationError
from src.application.queries.fleet.get_fleet_overview import (
    GET_FLEET_OVERVIEW,
    GetFleetOverviewQuery,
)
from src.application.results.fleet_overview import FleetOverview
from src.ports.input.query_bus import QueryBus

MODULE = "src.adapters.driving.cli.commands.get_fleet_overview"


class GetFleetOverviewCommandShould(unittest.TestCase):
    """Validate argument parsing, typed dispatch, and rendering delegation."""

    def setUp(self) -> None:
        """Create a query bus and representative fleet-overview result."""
        self.query_bus = MagicMock(spec=QueryBus)
        self.overview = cast(FleetOverview, MagicMock(spec=FleetOverview))
        self.query_bus.dispatch.return_value = self.overview

    def _command(self, *params: str) -> GetFleetOverview:
        """Return a command using the supplied raw CLI parameters."""
        return GetFleetOverview(params, self.query_bus)

    @patch(f"{MODULE}.render_fleet_overview", return_value="rendered overview")
    def test_uses_default_limit_dispatches_and_renders(self, render_mock: MagicMock) -> None:
        """Dispatch the documented default active-route limit."""
        result = self._command().execute()

        self.assertEqual(result, "rendered overview")
        self._assert_query(10)
        render_mock.assert_called_once_with(self.overview)

    @patch(f"{MODULE}.render_fleet_overview", return_value="rendered overview")
    def test_accepts_explicit_limits_at_supported_boundaries(
        self,
        render_mock: MagicMock,
    ) -> None:
        """Accept the minimum, maximum, and an interior active-route limit."""
        for limit in (1, 25, 100):
            with self.subTest(limit=limit):
                self.query_bus.reset_mock()
                self.query_bus.dispatch.return_value = self.overview
                render_mock.reset_mock()

                result = self._command(str(limit)).execute()

                self.assertEqual(result, "rendered overview")
                self._assert_query(limit)
                render_mock.assert_called_once_with(self.overview)

    @patch(f"{MODULE}.render_fleet_overview")
    def test_rejects_invalid_argument_shapes_before_dispatch(
        self,
        render_mock: MagicMock,
    ) -> None:
        """Reject extra, non-integer, non-positive, and oversized arguments."""
        invalid_params = (
            ("1", "2"),
            ("not-an-int",),
            ("0",),
            ("-1",),
            ("101",),
        )

        for params in invalid_params:
            with self.subTest(params=params), self.assertRaises(ValueError):
                self._command(*params).execute()

        self.query_bus.dispatch.assert_not_called()
        render_mock.assert_not_called()

    @patch(f"{MODULE}.render_fleet_overview")
    def test_propagates_query_bus_failures(self, render_mock: MagicMock) -> None:
        """Propagate application and persistence failures without rendering."""
        for error in (
            PermissionError("Unauthenticated"),
            ValidationError("invalid overview request"),
            RuntimeError("query failed"),
        ):
            with self.subTest(error=error):
                self.query_bus.reset_mock()
                self.query_bus.dispatch.side_effect = error

                with self.assertRaises(type(error)) as raised:
                    self._command().execute()

                self.assertIs(raised.exception, error)
                self._assert_query(10)
                render_mock.assert_not_called()

        self.query_bus.dispatch.side_effect = None

    @patch(f"{MODULE}.render_fleet_overview", side_effect=RuntimeError("render failed"))
    def test_propagates_renderer_failure_after_dispatch(self, render_mock: MagicMock) -> None:
        """Preserve renderer failures after successful query execution."""
        with self.assertRaisesRegex(RuntimeError, "render failed"):
            self._command().execute()

        self._assert_query(10)
        render_mock.assert_called_once_with(self.overview)

    def _assert_query(self, active_route_limit: int) -> None:
        """Assert one fleet-overview dispatch with the expected route limit."""
        self.query_bus.dispatch.assert_called_once()
        self.assertIs(self.query_bus.dispatch.call_args.kwargs["key"], GET_FLEET_OVERVIEW)
        query = self.query_bus.dispatch.call_args.kwargs["query"]
        self.assertIsInstance(query, GetFleetOverviewQuery)
        self.assertEqual(query.active_route_limit, active_route_limit)


if __name__ == "__main__":
    unittest.main()
