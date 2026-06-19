"""Validation for persisted truck runtime snapshots."""

from src.application.dto.world_state_snapshot_dto import TruckSnapshot, WorldSnapshotData
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.map import Map


class TruckSnapshotValidator:
    """Validate truck snapshot identity, references, locations, and runtime state."""

    def validate_truck_snapshots(
        self, world: WorldSnapshotData, *, schema_version: int, fleet_by_id: dict[int, Truck]
    ) -> None:
        """Ensure truck snapshots are complete and compatible with route assignments.

        Args:
            world: Snapshot payload containing truck and route snapshots.
            schema_version: Snapshot schema version.
            fleet_by_id: Runtime fleet trucks keyed by vehicle id.

        Raises:
            WorldStateCorruptionError: If truck snapshots are missing, duplicated,
                reference missing fleet trucks, or violate runtime invariants.
        """
        fleet_ids = set(fleet_by_id)
        route_trucks = {
            route.truck_vehicle_id: route.route_id
            for route in world.routes
            if route.truck_vehicle_id is not None
        }

        seen_truck_ids: set[int] = set()

        for truck in world.trucks:
            if truck.vehicle_id < 1:
                raise WorldStateCorruptionError(
                    f"Invalid truck id in snapshot: {truck.vehicle_id}",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

            if truck.vehicle_id in seen_truck_ids:
                raise WorldStateCorruptionError(
                    f"Duplicate truck id in snapshot: {truck.vehicle_id}",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )
            seen_truck_ids.add(truck.vehicle_id)

            if truck.vehicle_id not in fleet_ids:
                raise WorldStateCorruptionError(
                    f"Snapshot references missing truck {truck.vehicle_id}.",
                    reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                )

            if truck.status not in TruckStatus.values():
                raise WorldStateCorruptionError(
                    f"Truck {truck.vehicle_id} has invalid status {truck.status!r}.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

            status = TruckStatus(truck.status)
            self._validate_truck_snapshot_locations(truck)
            self._validate_truck_snapshot_runtime_state(truck, status)

            if truck.route_id is not None:
                expected_route_id = route_trucks.get(truck.vehicle_id)
                if expected_route_id != truck.route_id:
                    raise WorldStateCorruptionError(
                        f"Truck {truck.vehicle_id} points to route {truck.route_id}, "
                        f"but route assignment points to {expected_route_id}.",
                        reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                    )

        if schema_version == 2:
            missing_truck_ids = fleet_ids - seen_truck_ids
            if missing_truck_ids:
                missing = ", ".join(str(truck_id) for truck_id in sorted(missing_truck_ids))
                raise WorldStateCorruptionError(
                    f"Schema v2 snapshot is missing truck snapshots: {missing}.",
                    reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
                )

        trucks_by_snapshot_id = {truck.vehicle_id: truck for truck in world.trucks}

        for truck_vehicle_id, route_id in route_trucks.items():
            truck_snapshot = trucks_by_snapshot_id.get(truck_vehicle_id)
            if truck_snapshot is not None and truck_snapshot.route_id != route_id:
                raise WorldStateCorruptionError(
                    f"Route {route_id} assigns truck {truck_vehicle_id}, "
                    f"but truck snapshot points to route {truck_snapshot.route_id}.",
                    reason=WorldStateCorruptionReason.INVALID_REFERENCES,
                )

    @staticmethod
    def _validate_truck_snapshot_locations(truck: TruckSnapshot) -> None:
        """Validate persisted truck locations against the route map."""
        if truck.current_location is not None and not Map.is_valid_location(truck.current_location):
            raise WorldStateCorruptionError(
                f"Truck {truck.vehicle_id} has unsupported current location {truck.current_location}.",
                reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
            )

        if truck.in_transit_to is not None and not Map.is_valid_location(truck.in_transit_to):
            raise WorldStateCorruptionError(
                f"Truck {truck.vehicle_id} has unsupported transit destination {truck.in_transit_to}.",
                reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
            )

    @staticmethod
    def _validate_truck_snapshot_runtime_state(truck: TruckSnapshot, status: TruckStatus) -> None:
        """Validate status-specific truck runtime fields."""
        if status == TruckStatus.FREE:
            if truck.route_id is not None:
                raise WorldStateCorruptionError(
                    f"Free truck {truck.vehicle_id} cannot point to route {truck.route_id}.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )
            if truck.busy_from is not None or truck.busy_until is not None:
                raise WorldStateCorruptionError(
                    f"Free truck {truck.vehicle_id} cannot have a busy window.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )
            if truck.in_transit_to is not None:
                raise WorldStateCorruptionError(
                    f"Free truck {truck.vehicle_id} cannot be in transit.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )

        if status == TruckStatus.ON_THE_WAY and truck.route_id is None:
            raise WorldStateCorruptionError(
                f"On-the-way truck {truck.vehicle_id} must point to a route.",
                reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
            )
