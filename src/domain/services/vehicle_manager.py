from src.application.dto.truck_binding_dto import TruckBinding
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.map import Map
from src.ports.output.vehicle_manager import RouteSuitabilityView


class VehicleManager:
    def __init__(self) -> None:
        self.vehicles: list[Truck] = (
            [Truck(vehicle_id, "Scania", 42000, 8000) for vehicle_id in range(1001, 1011)]
            + [Truck(vehicle_id, "Man", 37000, 10000) for vehicle_id in range(1011, 1026)]
            + [Truck(vehicle_id, "Actros", 26000, 13000) for vehicle_id in range(1026, 1041)]
        )
        self.disperse_trucks()

    def disperse_trucks(self) -> None:
        """Deterministic round-robin by truck type across cities (no randomness)."""
        from collections import defaultdict

        locs = Map.get_locations()
        type_groups: dict[str, list[Truck]] = defaultdict(list)
        for t in self.vehicles:
            type_groups[t.name].append(t)

        i = 0
        for_type_keys = list(type_groups.keys())
        while any(type_groups.values()):
            for typ in for_type_keys:
                if type_groups[typ]:
                    t = type_groups[typ].pop(0)
                    t.current_location = locs[i % len(locs)]
                    i += 1

    def list_fleet(self) -> list[Truck]:
        return list(self.vehicles)

    def find_by_id(self, vehicle_id: int) -> Truck | None:
        for v in self.vehicles:
            if v.vehicle_id == vehicle_id:
                return v
        return None

    def is_suitable_for_route(self, truck: Truck, route: RouteSuitabilityView) -> tuple[bool, str]:
        if truck.max_range < route.total_distance_km:
            return False, "range too short"
        if truck.capacity < route.total_assigned_weight():
            return False, "insufficient capacity"
        if truck.current_location != route.start_location:
            return False, f"wrong location ({truck.current_location} != {route.start_location})"
        if truck.route is not None:
            if route.departure_time is None:
                return False, "route not scheduled yet"

            current_eta = truck.route.eta_final
            if current_eta is None:
                return False, "truck already assigned to a route with unknown availability"

            if current_eta >= route.departure_time:
                return False, "truck busy in the requested time window"

        return True, ""

    def find_available_for_route(self, route: DeliveryRoute) -> list[Truck]:
        result: list[Truck] = []
        for t in self.vehicles:
            ok, _ = self.is_suitable_for_route(t, route)
            if ok:
                result.append(t)
        result.sort(key=lambda t: t.vehicle_id)
        return result
    
    def replace_truck_bindings(self, bindings: list[TruckBinding]) -> None:
        for truck in self.vehicles:
            truck.route = None
            truck.status = TruckStatus.FREE
            truck.busy_from = None
            truck.busy_until = None
            truck.in_transit_to = None

        for binding in bindings:
            truck = binding.truck
            route = binding.route

            truck.status = binding.status
            truck.current_location = binding.current_location
            truck.busy_from = binding.busy_from
            truck.busy_until = binding.busy_until
            truck.in_transit_to = binding.in_transit_to
            truck.route = route
            if route is not None:
                route.truck = truck
