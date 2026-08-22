"""CLI command for viewing a package."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.adapters.driving.cli.rendering.package_info_renderer import render_package_info
from src.application.queries.packages.view_package import VIEW_PACKAGE, ViewPackageQuery


class ViewPackage(QueryBusCommand):
    """Render one package by id."""

    def execute(self) -> str:
        """Fetch a package and return display text.

        Returns:
            Multi-line package summary.

        Raises:
            PermissionError: If the caller lacks package view permission.
            ValueError: If the parameter count or id is invalid.
            NotFoundError: If the package does not exist.
            DatabaseError: If package retrieval fails.
        """
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0], "package_id")
        package = self.query_bus.dispatch(
            key=VIEW_PACKAGE,
            query=ViewPackageQuery(package_id=package_id),
        )
        return render_package_info(package)
