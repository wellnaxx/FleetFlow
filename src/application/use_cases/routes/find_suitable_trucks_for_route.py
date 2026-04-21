from src.domain.entities.truck import Truck
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.vehicle_manager import VehicleManagerPort


class FindSuitableTrucksForRouteUseCase:
    def __init__(self, routes: RouteRepositoryPort, vehicles: VehicleManagerPort) -> None:
        self._routes = routes
        self._vehicles = vehicles

    def execute(self, route_id: int) -> list[Truck]:
        route = self._routes.get_by_id(route_id)
        if route is None:
            raise ValueError(f"Route with ID {route_id} not found")
        return self._vehicles.find_available_for_route(route)
