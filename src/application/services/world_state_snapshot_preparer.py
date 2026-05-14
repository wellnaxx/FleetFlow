from collections.abc import Collection

from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot
from src.application.services.world_snapshot_validator import WorldStateSnapshotValidator
from src.application.services.world_state_linker import WorldStateSnapshotLinker
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_rebuilder import WorldStateSnapshotRebuilder


class WorldStateSnapshotPreparer:
    def __init__(
        self,
        reconciler: WorldStateReconciliationService,
        validator: WorldStateSnapshotValidator,
        rebuilder: WorldStateSnapshotRebuilder,
        linker: WorldStateSnapshotLinker,
    ) -> None:
        self._validator = validator
        self._rebuilder = rebuilder 
        self._linker = linker
        self._reconciler = reconciler

    def prepare(
        self, snapshot: WorldStateSnapshot, supported_schema_versions: Collection[int]
    ) -> ReconciledWorld:

        self._validator.validate_snapshot(snapshot, supported_schema_versions)

        rebuilt_world = self._rebuilder.rebuild(snapshot)
        linked_trucks = self._linker.link(snapshot, rebuilt_world)

        self._reconciler.reconcile_routes(
            routes=list(rebuilt_world.routes.values()),
            update_trucks=True,
        )
        truck_bindings = self._linker.build_truck_bindings(
            route_snapshots=snapshot.world.routes,
            routes=rebuilt_world.routes,
            trucks_by_route_id=linked_trucks.trucks_by_route_id,
            candidate_trucks_by_id=linked_trucks.candidate_trucks_by_id,
        )

        return ReconciledWorld(
            customers=rebuilt_world.customers,
            packages=rebuilt_world.packages,
            routes=rebuilt_world.routes,
            counters=snapshot.world.counters,
            truck_bindings=truck_bindings,
        )
