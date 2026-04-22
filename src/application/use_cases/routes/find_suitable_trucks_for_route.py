from src.domain.entities.truck import Truck
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.vehicle_manager import VehicleManagerPort


class FindSuitableTrucksForRouteUseCase:
    """Find trucks that can serve a route."""

    def __init__(self, routes: RouteRepositoryPort, vehicles: VehicleManagerPort) -> None:
        self._routes = routes
        self._vehicles = vehicles

    def execute(self, route_id: int) -> list[Truck]:
        """Return trucks that are currently suitable for a route.

        Args:
            route_id: Identifier of the route to evaluate.

        Returns:
            A list of suitable trucks.

        Raises:
            ValueError: If the route does not exist.
        """
        route = self._routes.get_by_id(route_id)
        if route is None:
            raise ValueError(f"Route with ID {route_id} not found")
        return self._vehicles.find_available_for_route(route)
