"""CLI command for assigning a truck to a route."""

from datetime import datetime

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase


class AssignTruckToRoute(EventDrainingCommand[AssignTruckToRouteUseCase]):
    """Assign a truck and publish use-case and route events."""

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Assign the requested truck to the requested route.

        Returns:
            CLI confirmation text.

        Raises:
            PermissionError: If the caller lacks truck-assignment permission.
            ValueError: If parameters are invalid or assignment fails.
            Exception: Propagates event-publication failures after successful
                use-case execution.
        """
        validate_params_exact(self._params, 2)

        truck_id = try_parse_int(self._params[0], "truck_id")
        route_id = try_parse_int(self._params[1], "route_id")
        now = datetime.now()

        result = self._run_and_drain(
            self._use_case,
            lambda: self._use_case.execute(truck_id, route_id, now),
        )

        self._event_collector.drain((result.route,))

        return f"Assigned truck {truck_id} to route {result.route_id}."
