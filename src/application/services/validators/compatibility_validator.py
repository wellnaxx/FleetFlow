"""Validation for route/package and truck/route compatibility rules."""

import itertools

from src.application.dto.world_state_snapshot_dto import PackageSnapshot, RouteSnapshot, WorldSnapshotData
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.domain.entities.truck import Truck
from src.domain.services.map import Map
from src.domain.value_objects.location_code import LocationCode


class CompatibilitySnapshotValidator:
    """Validate relationship compatibility after references are known to exist."""

    def validate_route_package_compatibility(self, world: WorldSnapshotData) -> None:
        """Ensure assigned packages can be carried by their referenced routes.

        Args:
            world: Snapshot payload containing packages and routes.

        Raises:
            WorldStateCorruptionError: If a package start/end is not on its route
                or appears in an invalid order.
        """
        routes_by_id = {route.route_id: route for route in world.routes}

        for package in world.packages:
            if package.route_id is None:
                continue

            route = routes_by_id[package.route_id]
            locations = route.locations

            if package.start not in locations:
                raise WorldStateCorruptionError(
                    f"Package {package.package_id} starts at {package.start}, "
                    f"which is not on route {route.route_id}.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

            if package.end not in locations:
                raise WorldStateCorruptionError(
                    f"Package {package.package_id} ends at {package.end}, "
                    f"which is not on route {route.route_id}.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

            if locations.index(package.start) >= locations.index(package.end):
                raise WorldStateCorruptionError(
                    f"Package {package.package_id} has invalid location order on route {route.route_id}.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

    def validate_truck_route_compatibility(
        self, world: WorldSnapshotData, fleet_by_id: dict[int, Truck]
    ) -> None:
        """Ensure assigned trucks can operate their referenced routes.

        Args:
            world: Snapshot payload containing packages and routes.
            fleet_by_id: Runtime fleet trucks keyed by vehicle id.

        Raises:
            WorldStateCorruptionError: If a truck is assigned to an unscheduled
                route or the route exceeds the truck's load or range limits.
        """
        trucks_by_id = fleet_by_id
        packages_by_id = {package.package_id: package for package in world.packages}

        for route in world.routes:
            truck_vehicle_id = route.truck_vehicle_id
            if truck_vehicle_id is None:
                continue

            if route.departure_time is None:
                raise WorldStateCorruptionError(
                    f"Route {route.route_id} assigns truck {truck_vehicle_id}, "
                    "but the route has no departure time.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

            truck = trucks_by_id[truck_vehicle_id]

            max_segment_load = self._route_max_segment_load(route, packages_by_id)
            if max_segment_load > truck.capacity:
                raise WorldStateCorruptionError(
                    f"Route {route.route_id} assigns truck {truck_vehicle_id}, "
                    f"but segment load {max_segment_load} exceeds capacity {truck.capacity}.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

            total_distance = self._route_distance_km(route.locations)
            if total_distance > truck.max_range:
                raise WorldStateCorruptionError(
                    f"Route {route.route_id} assigns truck {truck_vehicle_id}, "
                    f"but route distance {total_distance} exceeds range {truck.max_range}.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

    @staticmethod
    def _route_max_segment_load(route: RouteSnapshot, packages_by_id: dict[int, PackageSnapshot]) -> float:
        segment_loads = [0.0 for _ in range(len(route.locations) - 1)]
        location_index: dict[LocationCode, int] = {}
        for index, location in enumerate(route.locations):
            location_index.setdefault(location, index)

        for package_id in route.package_ids:
            package = packages_by_id[package_id]
            start_index = location_index.get(package.start)
            end_index = location_index.get(package.end)
            if start_index is None or end_index is None or start_index >= end_index:
                continue

            for segment_index in range(start_index, end_index):
                segment_loads[segment_index] += package.weight

        return max(segment_loads, default=0.0)

    @staticmethod
    def _route_distance_km(locations: tuple[LocationCode, ...]) -> int:
        total = 0

        for start, end in itertools.pairwise(locations):
            total += Map.get_distance(start, end)

        return total
