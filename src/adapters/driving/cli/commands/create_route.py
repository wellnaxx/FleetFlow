"""Command-bus-backed CLI command for creating delivery routes."""

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import (
    parse_departure_from_tail,
    validate_params_count,
)
from src.application.commands.routes.create_route import CREATE_ROUTE, CreateRouteCommand


class CreateRoute(CommandBusCommand):
    """Create a route through the application command bus.

    Usage:
        createroute <LOC1> <LOC2> [LOC3 ...] [YYYY-MM-DD HH:MM]

    Examples:
        createroute SYD MEL
        createroute SYD MEL ADL
        createroute SYD MEL "2025-10-12 06:00"
        createroute SYD MEL 2025-10-12 06:00
    """

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Create a route and return CLI confirmation text.

        Returns:
            Summary of the created route.

        Raises:
            PermissionError: If the caller lacks route creation permission.
            ValueError: If parameter validation or route creation fails.
            DatabaseError: If route persistence or event publication fails.
            DomainValidationError: If the route path or departure is invalid.
        """
        validate_params_count(self._params, 2)
        loc_tokens, departure = parse_departure_from_tail(list(self._params))
        route = self.command_bus.dispatch(
            key=CREATE_ROUTE,
            command=CreateRouteCommand(
                locations=tuple(loc_tokens),
                departure_time=departure,
            ),
        )

        dep_str = "(unscheduled)" if departure is None else departure.strftime("%Y-%m-%d %H:%M")
        return (
            f"Route {route.route_id} created: {' -> '.join(loc_tokens)} "
            f"| Departure: {dep_str} | Distance: {route.total_distance_km} km"
        )
