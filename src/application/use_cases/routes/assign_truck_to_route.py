from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.vehicle_manager import VehicleManagerPort


@dataclass(frozen=True)
class _RouteSuitabilityProbe:
    total_distance_km: int
    start_location: str
    departure_time: datetime
    assigned_weight: float

    def total_assigned_weight(self) -> float:
        return self.assigned_weight


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

        current_truck = route.truck
        if current_truck is not None:
            raise ValueError(f"Route {route_id} already has truck {current_truck.vehicle_id} assigned")

        effective_route: DeliveryRoute | _RouteSuitabilityProbe = route
        if route.departure_time is None:
            effective_route = _RouteSuitabilityProbe(
                total_distance_km=route.total_distance_km,
                start_location=route.start_location,
                departure_time=now,
                assigned_weight=route.total_assigned_weight(),
            )

        ok, reason = self._vehicles.is_suitable_for_route(truck, effective_route)
        if not ok:
            raise ValueError(
                f"Truck {truck_id} is not suitable for route {route_id}: {reason}. "
                f"Use 'findsuitabletrucksforroute {route_id}' to list options."
            )

        if route.departure_time is None:
            route.schedule(now)
        route.truck = truck
        truck.assign(route, route.start_location)

        return route
