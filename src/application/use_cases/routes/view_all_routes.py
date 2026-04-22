from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.route_repository import RouteRepositoryPort


class ViewAllRoutesUseCase:
    """List all routes from the repository."""

    def __init__(self, routes: RouteRepositoryPort) -> None:
        self._routes = routes

    def execute(self) -> list[DeliveryRoute]:
        """Return all persisted routes."""
        return self._routes.list_all()
