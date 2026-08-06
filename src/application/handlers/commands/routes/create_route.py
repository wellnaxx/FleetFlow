"""Command handler for route creation."""

from src.application.commands.routes.create_route import CreateRouteCommand
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.domain.entities.delivery_route import DeliveryRoute


class CreateRouteCommandHandler:
    """Adapt a route-creation command to the creation workflow."""

    def __init__(self, use_case: CreateRouteUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized route-creation workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, command: CreateRouteCommand) -> DeliveryRoute:
        """Create a route from its ordered locations and departure time.

        Args:
            command: Ordered route path and optional departure timestamp.

        Returns:
            Newly persisted route.

        Raises:
            Exception: Propagates authorization, validation, domain,
                persistence, and other failures raised by the use case.
        """
        return self._use_case.execute(command.locations, command.departure_time)
