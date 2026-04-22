from datetime import datetime

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.services.authorization_service import requires
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.domain.enums.auth import Permission


class AssignTruckToRoute(BaseCommand[AssignTruckToRouteUseCase]):
    """Assign a truck and start the route immediately (intended behavior).

    Preconditions:
        - The truck's current location must match the route's start location.
        - The route must have a valid schedule (or is auto-scheduled at now).
    Raises:
        ValueError: If entities are missing or preconditions fail.
    """

    mutates_state = True

    @requires(Permission.ROUTE_ASSIGN_TRUCK)
    def execute(self) -> str:
        validate_params_exact(self._params, 2)

        truck_id = try_parse_int(self._params[0])
        route_id = try_parse_int(self._params[1])
        now = datetime.now()

        result = self._use_case.execute(truck_id, route_id, now)

        return f"Assigned truck {truck_id} to route {result.route_id}."

