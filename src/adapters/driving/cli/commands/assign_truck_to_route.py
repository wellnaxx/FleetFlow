from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact


class AssignTruckToRoute(BaseCommand):
    """Assign a truck and start the route immediately (intended behavior).

    Preconditions:
        - The truck's current location must match the route's start location.
        - The route must have a valid schedule (or is auto-scheduled at now).
    Raises:
        ValueError: If entities are missing or preconditions fail.
    """

    mutates_state = True

    def execute(self) -> str:
        validate_params_exact(self._params, 2)
        truck_id = try_parse_int(self._params[0])
        route_id = try_parse_int(self._params[1])

        route = self._app_data.assign_truck_to_route(truck_id, route_id)
        return f"Assigned truck {truck_id} to route {route.route_id}."
