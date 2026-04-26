"""Use case for assigning a truck to a route."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from src.domain.value_objects.location_code import LocationCode
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.vehicle_manager import VehicleManagerPort

if TYPE_CHECKING:
    from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True)
class _RouteSuitabilityProbe:
    total_distance_km: int
    start_location: LocationCode
    departure_time: datetime
    assigned_weight: float

    def total_assigned_weight(self) -> float:
        """Return package weight assigned to the probed route."""
        return self.assigned_weight

    def maximum_segment_load(self) -> float:
        """Return maximum segment load for the probed route."""
        return self.assigned_weight


@dataclass(frozen=True)
class AssignTruckToRouteResult:
    """Result returned after a truck is assigned to a route."""

    route_id: int
    truck_id: int


class AssignTruckToRouteUseCase:
    """Assign a truck to a route after suitability checks."""

    def __init__(self, routes: RouteRepositoryPort, vehicles: VehicleManagerPort) -> None:
        """Initialize assignment dependencies.

        Args:
            routes: Repository used to fetch the target route.
            vehicles: Vehicle manager used to fetch and validate trucks.
        """
        self._routes = routes
        self._vehicles = vehicles

    def execute(self, truck_id: int, route_id: int, now: datetime) -> AssignTruckToRouteResult:
        """Assign a truck to a route.

        Args:
            truck_id: Identifier of the truck to assign.
            route_id: Identifier of the route to update.
            now: Clock value used when scheduling an unscheduled route.

        Returns:
            A summary of the successful truck assignment.

        Raises:
            ValueError: If the route or truck is missing, the route already has a
                truck, or the truck is unsuitable.
        """
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
                assigned_weight=route.maximum_segment_load(),
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
        truck.assign(route)

        return AssignTruckToRouteResult(route_id=route.route_id, truck_id=truck.vehicle_id)
