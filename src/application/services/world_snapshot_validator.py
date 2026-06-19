from collections.abc import Collection

from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot
from src.application.services.validators.compatibility_validator import CompatibilitySnapshotValidator
from src.application.services.validators.customer_validator import CustomerSnapshotValidator
from src.application.services.validators.identity_validator import IdentitySnapshotValidator
from src.application.services.validators.reference_validator import ReferenceSnapshotValidator
from src.application.services.validators.schema_validator import SchemaSnapshotValidator
from src.application.services.validators.truck_snapshot_validator import TruckSnapshotValidator
from src.ports.output.vehicle_manager import VehicleManagerPort


class WorldStateSnapshotValidator:
    """Coordinate focused validators for imported world-state snapshots."""

    def __init__(self, vehicle_manager: VehicleManagerPort) -> None:
        """Initialize validator dependencies.

        Args:
            vehicle_manager: Fleet service used to validate truck references and
                truck-route compatibility.
        """
        self._vehicle_manager = vehicle_manager
        self._schema = SchemaSnapshotValidator()
        self._identity = IdentitySnapshotValidator()
        self._references = ReferenceSnapshotValidator()
        self._trucks = TruckSnapshotValidator()
        self._compatibility = CompatibilitySnapshotValidator()
        self._customers = CustomerSnapshotValidator()

    def validate_snapshot(
        self, snapshot: WorldStateSnapshot, supported_schema_versions: Collection[int]
    ) -> None:
        """Validate a world-state snapshot before rebuilding or importing it.

        Args:
            snapshot: Snapshot DTO to validate.
            supported_schema_versions: Schema versions accepted by the caller.

        Raises:
            WorldStateCorruptionError: If any schema, identity, reference, or
                invariant validation fails.
        """
        world = snapshot.world

        fleet = self._vehicle_manager.list_fleet()
        fleet_by_id = {truck.vehicle_id: truck for truck in fleet}

        self._schema.validate(snapshot, supported_schema_versions)
        self._identity.validate_counters(world.counters)
        self._identity.validate_ids(world)
        self._references.validate_references(world, fleet_by_id)
        self._trucks.validate_truck_snapshots(
            world, schema_version=snapshot.schema_version, fleet_by_id=fleet_by_id
        )
        self._references.validate_route_package_consistency(world)
        self._compatibility.validate_route_package_compatibility(world)
        self._compatibility.validate_truck_route_compatibility(world, fleet_by_id)
        self._customers.validate_customer_uniqueness(world.customers)
        self._identity.validate_counter_bounds(world)
