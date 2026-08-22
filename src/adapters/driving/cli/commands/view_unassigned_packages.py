"""Query-bus-backed CLI command for listing unassigned packages."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.rendering.package_info_renderer import render_package_info
from src.application.queries.packages.view_unassigned_packages import (
    VIEW_UNASSIGNED_PACKAGES,
    ViewUnassignedPackagesQuery,
)


class ViewUnassignedPackages(QueryBusCommand):
    """Render packages that are not attached to a route."""

    def execute(self) -> str:
        """Return unassigned package listing text.

        Returns:
            CLI listing of unassigned packages, or an empty-state message.

        Raises:
            ValueError: If command arguments are supplied.
            PermissionError: If the caller lacks unassigned package permission.
            DatabaseError: If package retrieval fails.
        """
        if self.params:
            raise ValueError("viewunassignedpackages does not accept arguments.")

        packages = self.query_bus.dispatch(
            key=VIEW_UNASSIGNED_PACKAGES,
            query=ViewUnassignedPackagesQuery(),
        ).items
        if not packages:
            return "No unassigned packages."
        return "\n\n".join(render_package_info(package) for package in packages)
