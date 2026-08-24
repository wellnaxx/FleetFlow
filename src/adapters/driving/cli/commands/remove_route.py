"""Command-bus-backed CLI command for removing delivery routes."""

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.commands.routes.remove_route import REMOVE_ROUTE, RemoveRouteCommand


class RemoveRoute(CommandBusCommand):
    """Remove a route by id."""

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Remove the requested route.

        Returns:
            CLI confirmation text.

        Raises:
            PermissionError: If the caller lacks required route permissions.
            ValueError: If the route id is invalid.
            NotFoundError: If the route does not exist.
            DatabaseError: If route removal cannot be persisted.
        """
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0], "route_id")
        self.command_bus.dispatch(
            key=REMOVE_ROUTE,
            command=RemoveRouteCommand(route_id=route_id),
        )
        return f"Route {route_id} removed."
