"""Tests for the query-bus-backed truck-listing CLI adapter."""

import unittest
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks
from src.application.queries.trucks.view_all_trucks import VIEW_ALL_TRUCKS, ViewAllTrucksQuery
from src.ports.input.query_bus import QueryBus


class ViewAllTrucksShould(unittest.TestCase):
    """Verify query dispatch, rendering, and failure propagation."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)
        self.command = ViewAllTrucks((), self.query_bus)

    def test_propagates_permission_error_from_query_bus(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: TRUCK_VIEW")

        with self.assertRaisesRegex(PermissionError, "TRUCK_VIEW"):
            self.command.execute()

        self._assert_listing_dispatched()

    def test_returns_empty_state_when_no_trucks_exist(self) -> None:
        self.query_bus.dispatch.return_value = []

        result = self.command.execute()

        self.assertEqual(result, "No trucks.")
        self._assert_listing_dispatched()

    @patch("src.adapters.driving.cli.commands.view_all_trucks.render_truck_info")
    def test_renders_multiple_trucks_in_query_order(self, render: MagicMock) -> None:
        truck1 = MagicMock()
        truck2 = MagicMock()
        render.side_effect = ["Truck 1 Info", "Truck 2 Info"]
        self.query_bus.dispatch.return_value = [truck1, truck2]

        result = self.command.execute()

        self.assertEqual(result, "Truck 1 Info\n\nTruck 2 Info")
        self._assert_listing_dispatched()
        self.assertEqual(render.call_args_list, [call(truck1), call(truck2)])

    def _assert_listing_dispatched(self) -> None:
        """Assert dispatch of the canonical fieldless truck query."""
        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_TRUCKS,
            query=ViewAllTrucksQuery(),
        )
