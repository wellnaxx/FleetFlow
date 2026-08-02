"""Tests for the fleet-overview CLI command."""

import unittest
from typing import cast
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.get_fleet_overview import GetFleetOverview
from src.application.eventing.collector import EventCollector
from src.application.exceptions.application_errors import ValidationError
from src.application.results.fleet_overview import FleetOverview
from src.application.use_cases.fleet.get_overview import GetFleetOverviewUseCase

MODULE = "src.adapters.driving.cli.commands.get_fleet_overview"


class GetFleetOverviewCommandShould(unittest.TestCase):
    """Validate argument parsing, event draining, and rendering delegation."""

    def setUp(self) -> None:
        """Create command dependencies and a fleet-overview result."""
        self.use_case = MagicMock(spec=GetFleetOverviewUseCase)
        self.event_collector = MagicMock(spec=EventCollector)
        self.overview = cast(FleetOverview, MagicMock(spec=FleetOverview))
        self.use_case.execute.return_value = self.overview

    def _command(self, *params: str) -> GetFleetOverview:
        """Return a command using the supplied raw CLI parameters."""
        return GetFleetOverview(
            params,
            self.use_case,
            self.event_collector,
        )

    @patch(f"{MODULE}.render_fleet_overview", return_value="rendered overview")
    def test_uses_default_limit_drains_and_renders(
        self,
        render_mock: MagicMock,
    ) -> None:
        """Execute the default request through the event-draining boundary."""
        result = self._command().execute()

        self.assertEqual(result, "rendered overview")
        self.use_case.execute.assert_called_once_with(active_route_limit=10)
        self.event_collector.drain.assert_called_once_with((self.use_case,))
        render_mock.assert_called_once_with(self.overview)

    @patch(f"{MODULE}.render_fleet_overview", return_value="rendered overview")
    def test_accepts_explicit_limits_at_supported_boundaries(
        self,
        render_mock: MagicMock,
    ) -> None:
        """Accept the minimum, maximum, and an interior active-route limit."""
        for limit in (1, 25, 100):
            with self.subTest(limit=limit):
                self.use_case.reset_mock()
                self.event_collector.reset_mock()
                render_mock.reset_mock()

                result = self._command(str(limit)).execute()

                self.assertEqual(result, "rendered overview")
                self.use_case.execute.assert_called_once_with(active_route_limit=limit)
                self.event_collector.drain.assert_called_once_with((self.use_case,))
                render_mock.assert_called_once_with(self.overview)

    @patch(f"{MODULE}.render_fleet_overview")
    def test_rejects_invalid_argument_shapes_before_execution(
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

        self.use_case.execute.assert_not_called()
        self.event_collector.drain.assert_not_called()
        render_mock.assert_not_called()

    @patch(f"{MODULE}.render_fleet_overview")
    def test_drains_pending_events_when_use_case_fails(
        self,
        render_mock: MagicMock,
    ) -> None:
        """Drain authorization events before re-raising use-case failures."""
        for error in (
            PermissionError("Unauthenticated"),
            ValidationError("invalid overview request"),
            RuntimeError("query failed"),
        ):
            with self.subTest(error=error):
                self.use_case.reset_mock()
                self.event_collector.reset_mock()
                self.use_case.execute.side_effect = error

                with self.assertRaises(type(error)) as raised:
                    self._command().execute()

                self.assertIs(raised.exception, error)
                self.use_case.execute.assert_called_once_with(active_route_limit=10)
                self.event_collector.drain.assert_called_once_with((self.use_case,))
                render_mock.assert_not_called()

    @patch(f"{MODULE}.render_fleet_overview")
    def test_propagates_success_path_event_publication_failure_before_rendering(
        self,
        render_mock: MagicMock,
    ) -> None:
        """Do not render a result whose pending events failed to publish."""
        error = RuntimeError("collector failed")
        self.event_collector.drain.side_effect = error

        with self.assertRaisesRegex(RuntimeError, "collector failed") as raised:
            self._command().execute()

        self.assertIs(raised.exception, error)
        self.use_case.execute.assert_called_once_with(active_route_limit=10)
        render_mock.assert_not_called()

    @patch(f"{MODULE}.render_fleet_overview", side_effect=RuntimeError("render failed"))
    def test_propagates_renderer_failure_after_events_are_drained(
        self,
        render_mock: MagicMock,
    ) -> None:
        """Preserve renderer failures after successful use-case publication."""
        with self.assertRaisesRegex(RuntimeError, "render failed"):
            self._command().execute()

        self.event_collector.drain.assert_called_once_with((self.use_case,))
        render_mock.assert_called_once_with(self.overview)
