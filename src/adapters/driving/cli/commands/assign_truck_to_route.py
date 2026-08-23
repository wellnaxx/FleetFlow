"""Command-bus-backed CLI command for assigning a truck to a route."""

from datetime import datetime

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.commands.routes.assign_truck_to_route import (
    ASSIGN_TRUCK_TO_ROUTE,
    AssignTruckToRouteCommand,
)


class AssignTruckToRoute(CommandBusCommand):
    """Assign a truck to a route at the current business-local time."""

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Assign the requested truck to the requested route.

        Returns:
            CLI confirmation text.

        Raises:
            PermissionError: If the caller lacks truck-assignment permission.
            ValueError: If parameters are invalid or assignment fails.
            NotFoundError: If the target route or truck does not exist.
            ConflictError: If the route or truck cannot accept the assignment.
            DatabaseError: If assignment persistence or event publication
                fails.
        """
        validate_params_exact(self._params, 2)

        truck_id = try_parse_int(self._params[0], "truck_id")
        route_id = try_parse_int(self._params[1], "route_id")
        now = datetime.now()

        result = self.command_bus.dispatch(
            key=ASSIGN_TRUCK_TO_ROUTE,
            command=AssignTruckToRouteCommand(
                truck_id=truck_id,
                route_id=route_id,
                now=now,
            ),
        )

        return f"Assigned truck {truck_id} to route {result.route_id}."
