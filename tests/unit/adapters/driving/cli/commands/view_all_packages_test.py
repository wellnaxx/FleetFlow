"""Tests for the query-bus-backed package-listing CLI adapter."""

import unittest
from unittest.mock import MagicMock, call, patch

from src.adapters.driving.cli.commands.view_all_packages import ViewAllPackages
from src.application.queries.packages.view_all_packages import VIEW_ALL_PACKAGES, ViewAllPackagesQuery
from src.application.use_cases.pagination import PageResult
from src.ports.input.query_bus import QueryBus


class ViewAllPackagesShould(unittest.TestCase):
    """Verify argument handling, query dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)

    def make_command(self, params: tuple[str, ...] = ()) -> ViewAllPackages:
        """Build the adapter with raw parameters and the mocked bus."""
        return ViewAllPackages(params, self.query_bus)

    def test_dispatches_default_query_and_renders_empty_state(self) -> None:
        self.query_bus.dispatch.return_value = PageResult(
            items=(),
            total=None,
            limit=None,
            offset=0,
        )

        result = self.make_command().execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_PACKAGES,
            query=ViewAllPackagesQuery(),
        )
        self.assertEqual(result, "No packages.")

    @patch("src.adapters.driving.cli.commands.view_all_packages.render_package_info")
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
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: PACKAGE_VIEW_ALL")

        with self.assertRaisesRegex(PermissionError, "PACKAGE_VIEW_ALL"):
            self.make_command().execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_ALL_PACKAGES,
            query=ViewAllPackagesQuery(),
        )

    def test_propagates_query_bus_failure(self) -> None:
        self.query_bus.dispatch.side_effect = RuntimeError("database failure")

        with self.assertRaisesRegex(RuntimeError, "database failure"):
            self.make_command().execute()

        self.query_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
