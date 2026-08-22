"""CLI command for listing packages."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.rendering.package_info_renderer import render_package_info
from src.application.queries.packages.view_all_packages import VIEW_ALL_PACKAGES, ViewAllPackagesQuery


class ViewAllPackages(QueryBusCommand):
    """Render all packages."""

    def execute(self) -> str:
        """Return package listing text.

        Returns:
            CLI listing of packages, or an empty-state message.

        Raises:
            ValueError: If command arguments are supplied.
            PermissionError: If the caller lacks package listing permission.
            DatabaseError: If package retrieval fails.
        """
        if self.params:
            raise ValueError("viewallpackages does not accept arguments.")

        packages = self.query_bus.dispatch(
            key=VIEW_ALL_PACKAGES,
            query=ViewAllPackagesQuery(),
        ).items
        return "\n\n".join(render_package_info(package) for package in packages) if packages else "No packages."
