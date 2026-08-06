"""Command handler for assigning a truck to a route."""

from src.application.commands.routes.assign_truck_to_route import AssignTruckToRouteCommand
from src.application.results.assign_truck_to_route_result import AssignTruckToRouteResult
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase


class AssignTruckToRouteCommandHandler:
    """Adapt a timed truck-assignment command to the route workflow."""

    def __init__(self, use_case: AssignTruckToRouteUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized truck-assignment workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, command: AssignTruckToRouteCommand) -> AssignTruckToRouteResult:
        """Assign the requested truck to the target route.

        Args:
            command: Truck, route, and deterministic evaluation time.

        Returns:
            Assignment result produced by the use case.

        Raises:
            Exception: Propagates authorization, lookup, domain, persistence,
                and other failures raised by the use case.
        """
        return self._use_case.execute(
            truck_id=command.truck_id,
            route_id=command.route_id,
            now=command.now,
        )
