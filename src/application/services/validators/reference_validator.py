"""Validation for cross-entity references in world-state snapshots."""

from src.application.dto.world_state_snapshot_dto import WorldSnapshotData
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.domain.entities.truck import Truck


class ReferenceSnapshotValidator:
    """Validate missing references and bidirectional relationship consistency."""

    def validate_references(self, world: WorldSnapshotData, fleet_by_id: dict[int, Truck]) -> None:
        """Ensure snapshot references point to existing customers, packages, routes, and trucks.

        Args:
            world: Snapshot payload containing entity relationship ids.
            fleet_by_id: Runtime fleet trucks keyed by vehicle id.

        Raises:
            WorldStateCorruptionError: If a snapshot reference points to a missing
                entity or assigns one truck to multiple routes.
        """
        customer_ids = {customer.customer_id for customer in world.customers}
        package_ids = {package.package_id for package in world.packages}
        route_ids = {route.route_id for route in world.routes}
        assigned_truck_ids: set[int] = set()

        for package in world.packages:
            if package.customer_id not in customer_ids:
                raise WorldStateCorruptionError(
                    f"Package {package.package_id} references missing customer {package.customer_id}.",
                    reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                )
            if package.route_id is not None and package.route_id not in route_ids:
                raise WorldStateCorruptionError(
                    f"Package {package.package_id} references missing route {package.route_id}.",
                    reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                )

        for route in world.routes:
            for package_id in route.package_ids:
                if package_id not in package_ids:
                    raise WorldStateCorruptionError(
                        f"Route {route.route_id} references missing package {package_id}.",
                        reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                    )
            truck_vehicle_id = route.truck_vehicle_id
            if truck_vehicle_id is None:
                continue
            if truck_vehicle_id not in fleet_by_id:
                raise WorldStateCorruptionError(
                    f"Route {route.route_id} references missing truck {truck_vehicle_id}.",
                    reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                )
            if truck_vehicle_id in assigned_truck_ids:
                raise WorldStateCorruptionError(
                    f"Truck {truck_vehicle_id} is assigned to multiple routes in snapshot.",
                    reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                )
            assigned_truck_ids.add(truck_vehicle_id)

    def validate_route_package_consistency(self, world: WorldSnapshotData) -> None:
        """Ensure route-package links agree in both directions.

        Args:
            world: Snapshot payload containing routes and packages.

        Raises:
            WorldStateCorruptionError: If a package points to a route that does
                not include it, or a route includes a package that points elsewhere.
        """
        route_packages: dict[int, set[int]] = {route.route_id: set(route.package_ids) for route in world.routes}
        package_route_ids = {package.package_id: package.route_id for package in world.packages}

        for package in world.packages:
            if package.route_id is None:
                continue

            if package.package_id not in route_packages.get(package.route_id, set()):
                raise WorldStateCorruptionError(
                    f"Package {package.package_id} points to route {package.route_id}, "
                    "but the route does not include that package.",
                    reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                )

        for route in world.routes:
            for package_id in route.package_ids:
                package_route_id = package_route_ids.get(package_id)
                if package_route_id != route.route_id:
                    raise WorldStateCorruptionError(
                        f"Route {route.route_id} includes package {package_id}, "
                        f"but the package points to route {package_route_id}.",
                        reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                    )
