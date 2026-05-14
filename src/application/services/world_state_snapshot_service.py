"""Build, validate, reconcile, and apply world-state snapshots."""

from typing import Protocol

from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldStateSnapshot,
)
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.application.services.world_state_schema import SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder
from src.application.services.world_state_snapshot_preparer import WorldStateSnapshotPreparer
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

    def __init__(
        self,
        customer_repo: CustomerSnapshotRepositoryPort,
        package_repo: PackageSnapshotRepositoryPort,
        route_repo: RouteSnapshotRepositoryPort,
        vehicle_manager: VehicleManagerPort,
        runtime_state: WorldStateRuntimePort,
        builder: WorldStateSnapshotBuilder,
        preparer: WorldStateSnapshotPreparer,
    ) -> None:
        """Initialize snapshot service dependencies.

        Args:
            customer_repo: Repository containing live customer aggregates.
            package_repo: Repository containing live package aggregates.
            route_repo: Repository containing live route aggregates.
            vehicle_manager: Fleet service used to snapshot and validate trucks.
            runtime_state: Runtime boundary used for atomic state replacement.
            builder: Service used to build world-state snapshots.
            preparer: Service used to prepare loaded snapshots for application.
        """
        self._customer_repo = customer_repo
        self._package_repo = package_repo
        self._route_repo = route_repo
        self._vehicle_manager = vehicle_manager
        self._runtime_state = runtime_state
        self._builder = builder
        self._preparer = preparer

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
            schema_version=SCHEMA_VERSION,
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
            reconciled_world = self._preparer.prepare(snapshot, SUPPORTED_SCHEMA_VERSIONS)
        except (KeyError, TypeError, ValueError) as exc:
            raise WorldStateCorruptionError(f"Invalid world state snapshot: {exc}") from exc

        self._swap_runtime_state(reconciled_world)

    def _swap_runtime_state(self, world: ReconciledWorld) -> None:
        self._runtime_state.replace_world_state(
            customers_by_id=world.customers,
            packages_by_id=world.packages,
            routes_by_id=world.routes,
            counters=world.counters,
            truck_bindings=world.truck_bindings,
        )
