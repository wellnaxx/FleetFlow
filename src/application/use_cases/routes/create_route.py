from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.services.map import Map
from src.ports.output.route_repository import RouteRepositoryPort


class CreateRouteUseCase:
    def __init__(self, routes: RouteRepositoryPort) -> None:
        self._routes = routes

    def execute(self, locations: list[str], departure_time: datetime | None) -> DeliveryRoute:
        if len(locations) < 2:
            raise ValueError("Invalid number of locations. A route must contain at least 2 locations.")

        for location in locations:
            if not Map.is_valid_location(location):
                raise ValueError(f"Invalid location: {location}")

        route = DeliveryRoute(
            *locations,
            departure_time=departure_time,
            route_id=self._routes.next_id(),
        )
        self._routes.add(route)
        return route
