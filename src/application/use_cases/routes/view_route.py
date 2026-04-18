from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.route_repository import RouteRepositoryPort


class ViewRouteUseCase:
    def __init__(self, routes: RouteRepositoryPort) -> None:
        self._routes = routes

    def execute(self, route_id: int) -> DeliveryRoute:
        route = self._routes.get_by_id(route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")
        return route