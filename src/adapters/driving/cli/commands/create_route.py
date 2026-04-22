from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import (
    parse_departure_from_tail,
    validate_params_count,
)
from src.application.services.authorization_service import requires
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.domain.enums.auth import Permission


class CreateRoute(BaseCommand[CreateRouteUseCase]):
    """
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

    @requires(Permission.ROUTE_CREATE)
    def execute(self) -> str:
        validate_params_count(self._params, 2)
        loc_tokens, departure = parse_departure_from_tail(list(self._params))
        route = self._use_case.execute(loc_tokens, departure)
        dep_str = "(unscheduled)" if departure is None else departure.strftime("%Y-%m-%d %H:%M")
        return (
            f"Route {route.route_id} created: {' -> '.join(loc_tokens)} "
            f"| Departure: {dep_str} | Distance: {route.total_distance_km} km"
        )
