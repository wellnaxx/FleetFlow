"""Query-bus-backed CLI command for listing routes."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.rendering.route_info_renderer import render_route_info
from src.application.queries.routes.view_all_routes import VIEW_ALL_ROUTES, ViewAllRoutesQuery


class ViewAllRoutes(QueryBusCommand):
    """Render all routes."""

    def execute(self) -> str:
        """Return route listing text.

        Returns:
            CLI listing of routes, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks route listing permission.
            DatabaseError: If route retrieval fails.
            ValidationError: If the pagination contract is invalid.
        """
        routes = self.query_bus.dispatch(
            key=VIEW_ALL_ROUTES,
            query=ViewAllRoutesQuery(),
        ).items
        return "\n\n".join(render_route_info(route) for route in routes) if routes else "No routes available."
