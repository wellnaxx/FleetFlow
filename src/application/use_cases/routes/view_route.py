from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.route_repository import RouteRepositoryPort


class ViewRouteUseCase:
    """Fetch one route by id."""

    def __init__(self, routes: RouteRepositoryPort) -> None:
        self._routes = routes

    def execute(self, route_id: int) -> DeliveryRoute:
        """Return one route by id.

        Args:
            route_id: Identifier of the route to fetch.

        Returns:
            The matching route entity.

        Raises:
            ValueError: If the route does not exist.
        """
        route = self._routes.get_by_id(route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")
        return route
