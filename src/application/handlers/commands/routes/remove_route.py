"""Command handler for route removal."""

from src.application.commands.routes.remove_route import RemoveRouteCommand
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.domain.entities.delivery_route import DeliveryRoute


class RemoveRouteCommandHandler:
    """Adapt a route-removal command to the removal workflow."""

    def __init__(self, use_case: RemoveRouteUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized route-removal workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, command: RemoveRouteCommand) -> DeliveryRoute:
        """Remove the identified route and coordinate assignment cleanup.

        Args:
            command: Identifier of the route to remove.

        Returns:
            Removed route produced by the use case.

        Raises:
            Exception: Propagates authorization, lookup, domain, persistence,
                and other failures raised by the use case.
        """
        return self._use_case.execute(command.route_id)
