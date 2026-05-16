"""CLI command for creating delivery routes."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import (
    parse_departure_from_tail,
    validate_params_count,
)
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.domain.value_objects.location_code import LocationCode


class CreateRoute(BaseCommand[CreateRouteUseCase]):
    """Create a route from location tokens and an optional departure time.

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
        """
        validate_params_count(self._params, 2)
        loc_tokens, departure = parse_departure_from_tail(list(self._params))
        locations = [LocationCode(token) for token in loc_tokens]
        route = self._use_case.execute(locations, departure)
        dep_str = "(unscheduled)" if departure is None else departure.strftime("%Y-%m-%d %H:%M")
        return (
            f"Route {route.route_id} created: {' -> '.join(locations)} "
            f"| Departure: {dep_str} | Distance: {route.total_distance_km} km"
        )
