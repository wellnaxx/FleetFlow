"""Tests for the query-bus-backed unassigned-package CLI adapter."""

import unittest
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages
from src.application.queries.packages.view_unassigned_packages import (
    VIEW_UNASSIGNED_PACKAGES,
    ViewUnassignedPackagesQuery,
)
from src.application.use_cases.pagination import PageResult
from src.ports.input.query_bus import QueryBus


class ViewUnassignedPackagesShould(unittest.TestCase):
    """Verify argument handling, query dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)

    def make_command(self, params: tuple[str, ...] = ()) -> ViewUnassignedPackages:
        """Build the adapter with raw parameters and the mocked bus."""
        return ViewUnassignedPackages(params, self.query_bus)

    def test_dispatches_default_query_and_renders_empty_state(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(),
            total=None,
            limit=None,
            offset=0,
        )

        result = self.make_command().execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_UNASSIGNED_PACKAGES,
            query=ViewUnassignedPackagesQuery(),
        )
        self.assertEqual(result, "No unassigned packages.")

    @patch("src.adapters.driving.cli.commands.view_unassigned_packages.render_package_info")
    def test_renders_multiple_packages_in_result_order(self, render: MagicMock) -> None:
        first = MagicMock()
        second = MagicMock()
        self.query_bus.dispatch.return_value = PageResult(
            items=(first, second),
            total=None,
            limit=None,
            offset=0,
        )
        render.side_effect = ["Package 1 Info", "Package 2 Info"]

        result = self.make_command().execute()

        self.assertEqual(result, "Package 1 Info\n\nPackage 2 Info")
        self.assertEqual(render.call_args_list, [call(first), call(second)])

    def test_rejects_unexpected_arguments_without_dispatching(self) -> None:
        command = self.make_command(("unexpected",))

        with self.assertRaisesRegex(ValueError, "does not accept arguments"):
            command.execute()

        self.query_bus.dispatch.assert_not_called()

    def test_propagates_permission_error_from_query_bus(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: PACKAGE_VIEW_UNASSIGNED")

        with self.assertRaisesRegex(PermissionError, "PACKAGE_VIEW_UNASSIGNED"):
            self.make_command().execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_UNASSIGNED_PACKAGES,
            query=ViewUnassignedPackagesQuery(),
        )

    def test_propagates_query_bus_failure(self) -> None:
        self.query_bus.dispatch.side_effect = RuntimeError("database failure")

        with self.assertRaisesRegex(RuntimeError, "database failure"):
            self.make_command().execute()

        self.query_bus.dispatch.assert_called_once()

    def test_has_no_mutation_flags(self) -> None:
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_state", False))
        self.assertFalse(getattr(ViewUnassignedPackages, "mutates_session", False))


if __name__ == "__main__":
    unittest.main()
