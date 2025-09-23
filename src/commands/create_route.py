from src.commands.base_command.base_command import BaseCommand
from src.commands.validation_helpers import validate_params_count, parse_departure_from_tail

class CreateRoute(BaseCommand):

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
    def execute(self):
        validate_params_count(self._params, 2)
        loc_tokens, departure = parse_departure_from_tail(list(self._params))
        route = self._app_data.create_route(loc_tokens, departure)
        dep_str = "(unscheduled)" if departure is None else departure.strftime("%Y-%m-%d %H:%M")
        return f"Route {route.route_id} created: {' -> '.join(loc_tokens)} | Departure: {dep_str} | Distance: {route.total_distance_km} km"
