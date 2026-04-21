from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.vehicle_manager import VehicleManagerPort


class AssignTruckToRouteUseCase:
    def __init__(self, routes: RouteRepositoryPort, vehicles: VehicleManagerPort) -> None:
        self._routes = routes
        self._vehicles = vehicles

    def execute(self, truck_id: int, route_id: int, now: datetime) -> DeliveryRoute:
        route = self._routes.get_by_id(route_id)
        if route is None:
            raise ValueError(f"Route with ID {route_id} not found")
        
        truck = self._vehicles.find_by_id(truck_id)
        if not truck:
            raise ValueError(f"Truck with ID {truck_id} not found")
        
        if route.departure_time is None:
            route.schedule(now)

        ok, reason = self._vehicles.is_suitable_for_route(truck, route)
        if not ok:
            raise ValueError(
                f"Truck {truck_id} is not suitable for route {route_id}: {reason}. "
                f"Use 'findsuitabletrucksforroute {route_id}' to list options."
            )

        route.truck = truck
        truck.assign(route, route.start_location)

        return route