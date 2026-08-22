"""Tests for the query-bus-backed package-detail CLI adapter."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_package import ViewPackage
from src.application.exceptions.application_errors import NotFoundError
from src.application.queries.packages.view_package import VIEW_PACKAGE, ViewPackageQuery
from src.ports.input.query_bus import QueryBus


class ViewPackageShould(unittest.TestCase):
    """Verify package-id parsing, query dispatch, rendering, and failures."""

    def setUp(self) -> None:
        """Create an isolated query bus for each test."""
        self.query_bus = MagicMock(spec=QueryBus)

    def make_command(self, params: tuple[str, ...]) -> ViewPackage:
        """Build the adapter with raw parameters and the mocked bus."""
        return ViewPackage(params, self.query_bus)

    @patch("src.adapters.driving.cli.commands.view_package.render_package_info")
    def test_dispatches_query_and_renders_package(self, render: MagicMock) -> None:
        package = MagicMock()
        self.query_bus.dispatch.return_value = package
        render.return_value = "Package 123 details"

        result = self.make_command(("123",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_PACKAGE,
            query=ViewPackageQuery(package_id=123),
        )
        render.assert_called_once_with(package)
        self.assertEqual(result, "Package 123 details")

    def test_propagates_permission_error_from_query_bus(self) -> None:
        self.query_bus.dispatch.side_effect = PermissionError("Missing permission: PACKAGE_VIEW")

        with self.assertRaisesRegex(PermissionError, "PACKAGE_VIEW"):
            self.make_command(("123",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_PACKAGE,
            query=ViewPackageQuery(package_id=123),
        )

    @patch("src.adapters.driving.cli.commands.view_package.try_parse_int")
    @patch("src.adapters.driving.cli.commands.view_package.validate_params_exact")
    def test_parameter_count_failure_prevents_parsing_and_dispatch(
        self,
        validate: MagicMock,
        parse_int: MagicMock,
    ) -> None:
        validate.side_effect = ValueError("Expected 1 parameter(s).")

        with self.assertRaisesRegex(ValueError, "Expected 1 parameter"):
            self.make_command(()).execute()

        validate.assert_called_once_with((), 1)
        parse_int.assert_not_called()
        self.query_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.view_package.try_parse_int")
    def test_invalid_identifier_prevents_dispatch(self, parse_int: MagicMock) -> None:
        parse_int.side_effect = ValueError("Parameter 'abc' is not a valid integer.")

        with self.assertRaisesRegex(ValueError, "not a valid integer"):
            self.make_command(("abc",)).execute()

        parse_int.assert_called_once_with("abc", "package_id")
        self.query_bus.dispatch.assert_not_called()

    def test_propagates_not_found_error_from_query_bus(self) -> None:
        self.query_bus.dispatch.side_effect = NotFoundError("Package with ID 999 not found")

        with self.assertRaisesRegex(NotFoundError, "Package with ID 999 not found"):
            self.make_command(("999",)).execute()

        self.query_bus.dispatch.assert_called_once_with(
            key=VIEW_PACKAGE,
            query=ViewPackageQuery(package_id=999),
        )


if __name__ == "__main__":
    unittest.main()
