"""Use case for listing all routes."""

from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.route_repository import RouteRepositoryPort


class ViewAllRoutesUseCase:
    """List all routes from the repository."""

    def __init__(self, routes: RouteRepositoryPort) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to list routes.
        """
        self._routes = routes

    def execute(self) -> list[DeliveryRoute]:
        """Return all persisted routes.

        Returns:
            Route entities currently stored in the repository.
        """
        return self._routes.list_all()
