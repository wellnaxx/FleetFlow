from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.route_repository import RouteRepositoryPort


class RemoveRouteUseCase:
    """Remove a route and detach its packages and truck."""

    def __init__(self, routes: RouteRepositoryPort) -> None:
        self._routes = routes

    def execute(self, route_id: int) -> DeliveryRoute:
        """Remove a route by id.

        Args:
            route_id: Identifier of the route to remove.

        Returns:
            The removed route entity.

        Raises:
            ValueError: If the route does not exist.
        """
        route = self._routes.get_by_id(route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")

        for package in list(getattr(route, "packages", [])):
            route.detach_package(package)

        if route.truck is not None:
            route.truck.release(force=True)

        self._routes.remove(route_id)
        return route
