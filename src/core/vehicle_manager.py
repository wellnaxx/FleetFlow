from src.models.delivery_route import DeliveryRoute
from src.models.map import Map
from src.models.truck import Truck


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

    def find_by_id(self, veh_id: int) -> Truck | None:
        for v in self.vehicles:
            if v.vehicle_id == veh_id:
                return v
        return None

    def is_suitable_for_route(self, truck: Truck, route: DeliveryRoute) -> tuple[bool, str]:
        if truck.max_range < route.total_distance_km:
            return False, "range too short"
        if truck.capacity < route.total_assigned_weight():
            return False, "insufficient capacity"
        if truck.current_location != route.start_location:
            return False, f"wrong location ({truck.current_location} != {route.start_location})"
        if truck.route and route.departure_time:
            if truck.route.eta_final and truck.route.eta_final >= route.departure_time:
                return False, "truck busy in the requested time window"
        elif truck.route and not route.departure_time:
            return False, "route not scheduled yet"
        return True, ""

    def find_available_for_route(self, route: DeliveryRoute) -> list[Truck]:
        result: list[Truck] = []
        for t in self.vehicles:
            ok, _ = self.is_suitable_for_route(t, route)
            if ok:
                result.append(t)
        result.sort(key=lambda t: t.vehicle_id)
        return result
