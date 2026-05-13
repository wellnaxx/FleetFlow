"""Build, validate, reconcile, and apply world-state snapshots."""

from typing import ClassVar, Protocol

from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldStateSnapshot,
)
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.application.services.world_snapshot_validator import WorldStateSnapshotValidator
from src.application.services.world_state_linker import WorldStateLinker
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder
from src.application.services.world_state_snapshot_rebuilder import WorldStateSnapshotRebuilder
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.vehicle_manager import VehicleManagerPort
from src.ports.output.world_state_runtime_port import WorldStateRuntimePort


class CustomerSnapshotRepositoryPort(Protocol):
    """Customer repository behavior required by world-state snapshots."""

    def peek_next_id(self) -> int:
        """Return the repository id counter to preserve in a snapshot."""
        ...

    def list_all(self) -> list[Customer]:
        """Return all customers."""
        ...


class PackageSnapshotRepositoryPort(Protocol):
    """Package repository behavior required by world-state snapshots."""

    def peek_next_id(self) -> int:
        """Return the repository id counter to preserve in a snapshot."""
        ...

    def list_all(self) -> list[DeliveryPackage]:
        """Return all packages."""
        ...


class RouteSnapshotRepositoryPort(Protocol):
    """Route repository behavior required by world-state snapshots."""

    def peek_next_id(self) -> int:
        """Return the repository id counter to preserve in a snapshot."""
        ...

    def list_all(self) -> list[DeliveryRoute]:
        """Return all routes."""
        ...


class WorldStateSnapshotService:
    """Coordinates snapshot creation and atomic snapshot application."""

    SCHEMA_VERSION: ClassVar[int] = 2
    SUPPORTED_SCHEMA_VERSIONS: ClassVar[frozenset[int]] = frozenset({1, 2})

    def __init__(
        self,
        customer_repo: CustomerSnapshotRepositoryPort,
        package_repo: PackageSnapshotRepositoryPort,
        route_repo: RouteSnapshotRepositoryPort,
        vehicle_manager: VehicleManagerPort,
        runtime_state: WorldStateRuntimePort,
        reconciler: WorldStateReconciliationService,
        builder: WorldStateSnapshotBuilder | None = None,
        validator: WorldStateSnapshotValidator | None = None,
        rebuilder: WorldStateSnapshotRebuilder | None = None,
        linker: WorldStateLinker | None = None,
    ) -> None:
        """Initialize snapshot service dependencies.

        Args:
            customer_repo: Repository containing live customer aggregates.
            package_repo: Repository containing live package aggregates.
            route_repo: Repository containing live route aggregates.
            vehicle_manager: Fleet service used to snapshot and validate trucks.
            runtime_state: Runtime boundary used for atomic state replacement.
            reconciler: Service used to reconcile candidate loaded state.
            builder: Snapshot builder. When omitted, a default builder is used.
            validator: Snapshot validator. When omitted, a default validator is used.
            rebuilder: Snapshot rebuilder. When omitted, a default rebuilder is used.
            linker: Snapshot linker. When omitted, a default linker is used.
        """
        self._customer_repo = customer_repo
        self._package_repo = package_repo
        self._route_repo = route_repo
        self._vehicle_manager = vehicle_manager
        self._runtime_state = runtime_state
        self._reconciler = reconciler
        self._builder = builder or WorldStateSnapshotBuilder()
        self._validator = validator or WorldStateSnapshotValidator(vehicle_manager)
        self._rebuilder = rebuilder or WorldStateSnapshotRebuilder()
        self._linker = linker or WorldStateLinker(vehicle_manager)

    def build_snapshot(self) -> WorldStateSnapshot:
        """Build a canonical snapshot from current runtime state.

        Returns:
            Versioned world-state snapshot containing customers, packages,
            routes, counters, and truck runtime state.
        """
        return self._builder.build_world_state_snapshot(
            customers=self._customer_repo.list_all(),
            packages=self._package_repo.list_all(),
            routes=self._route_repo.list_all(),
            trucks=self._vehicle_manager.list_fleet(),
            counters=self._build_counters_snapshot(),
            schema_version=self.SCHEMA_VERSION,
        )

    def _build_counters_snapshot(self) -> CountersSnapshot:
        return CountersSnapshot(
            next_customer_id=self._customer_repo.peek_next_id(),
            next_package_id=self._package_repo.peek_next_id(),
            next_route_id=self._route_repo.peek_next_id(),
        )

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        """Validate and apply a snapshot through one runtime replacement boundary.

        Args:
            snapshot: Persisted or in-memory snapshot to apply.

        Raises:
            WorldStateCorruptionError: If snapshot data is malformed or violates
                load-time invariants before runtime replacement.
        """
        try:
            reconciled_world = self._prepare_snapshot_for_swap(snapshot)
        except (KeyError, TypeError, ValueError) as exc:
            raise WorldStateCorruptionError(f"Invalid world state snapshot: {exc}") from exc

        self._swap_runtime_state(reconciled_world)

    def _prepare_snapshot_for_swap(self, snapshot: WorldStateSnapshot) -> ReconciledWorld:
        world = snapshot.world

        self._validator.validate_snapshot(snapshot, self.SUPPORTED_SCHEMA_VERSIONS)

        rebuilt_world = self._rebuilder.rebuild(snapshot)
        rebuilt_customers = rebuilt_world.customers
        rebuilt_packages = rebuilt_world.packages
        rebuilt_routes = rebuilt_world.routes

        linked_trucks = self._linker.link(snapshot, rebuilt_world)

        self._reconciler.reconcile_routes(
            routes=list(rebuilt_routes.values()),
            update_trucks=True,
        )
        truck_bindings = self._linker.build_truck_bindings(
            route_snapshots=world.routes,
            routes=rebuilt_routes,
            trucks_by_route_id=linked_trucks.trucks_by_route_id,
            candidate_trucks_by_id=linked_trucks.candidate_trucks_by_id,
        )

        return ReconciledWorld(
            customers=rebuilt_customers,
            packages=rebuilt_packages,
            routes=rebuilt_routes,
            counters=world.counters,
            truck_bindings=truck_bindings,
        )

    def _swap_runtime_state(self, world: ReconciledWorld) -> None:
        self._runtime_state.replace_world_state(
            customers_by_id=world.customers,
            packages_by_id=world.packages,
            routes_by_id=world.routes,
            counters=world.counters,
            truck_bindings=world.truck_bindings,
        )
