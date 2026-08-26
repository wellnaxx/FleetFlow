"""Query-bus-backed CLI command for viewing a route."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.adapters.driving.cli.rendering.route_info_renderer import render_route_info
from src.application.queries.routes.view_route import VIEW_ROUTE, ViewRouteQuery


class ViewRoute(QueryBusCommand):
    """Render one route by id."""

    def execute(self) -> str:
        """Fetch a route and return display text.

        Returns:
            Multi-line route summary.

        Raises:
            PermissionError: If the caller lacks route view permission.
            ValueError: If the parameter count or route id is invalid.
            NotFoundError: If the route does not exist.
            DatabaseError: If route retrieval fails.
        """
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0], "route_id")
        route = self.query_bus.dispatch(
            key=VIEW_ROUTE,
            query=ViewRouteQuery(route_id=route_id),
        )
        return render_route_info(route)
