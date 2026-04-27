"""Use case for creating a delivery route."""

from collections.abc import Sequence
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.services.map import Map
from src.domain.value_objects.location_code import LocationCode
from src.ports.output.route_repository import RouteRepositoryPort


class CreateRouteUseCase:
    """Create and persist delivery routes."""

    def __init__(self, routes: RouteRepositoryPort) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to allocate and persist routes.
        """
        self._routes = routes

    def execute(
        self, locations: Sequence[str | LocationCode], departure_time: datetime | None
    ) -> DeliveryRoute:
        """Create and persist a delivery route.

        Args:
            locations: Ordered list of raw or typed route stops.
            departure_time: Optional initial departure time.

        Returns:
            The newly created route.

        Raises:
            ValueError: If the route has too few stops or contains invalid
                locations.
        """
        if len(locations) < 2:
            raise ValueError("Invalid number of locations. A route must contain at least 2 locations.")

        for location in locations:
            if not Map.is_valid_location(location):
                raise ValueError(f"Invalid location: {location}")

        route = DeliveryRoute(
            *locations,
            departure_time=departure_time,
            route_id=self._routes.peek_next_id(),
        )
        self._routes.add(route)
        return route
