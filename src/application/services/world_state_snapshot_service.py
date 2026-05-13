"""Build, validate, reconcile, and apply world-state snapshots."""

from collections.abc import Mapping
from typing import ClassVar, Protocol

from src.adapters.driven.persistence.json.serialization import dt_from_str
from src.application.dto.candidate_truck_dto import CandidateTruckLink
from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    RouteSnapshot,
    TruckSnapshot,
    WorldStateSnapshot,
)
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.application.services.world_snapshot_validator import WorldStateSnapshotValidator
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder
from src.application.services.world_state_snapshot_rebuilder import WorldStateSnapshotRebuilder
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
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

        self._link_packages_to_routes(
            snapshots=world.routes,
            rebuilt_packages=rebuilt_packages,
            rebuilt_routes=rebuilt_routes,
        )

        truck_bindings = self._reconcile_candidate_world(
            route_snapshots=world.routes,
            truck_snapshots=world.trucks,
            routes=rebuilt_routes,
        )

        return ReconciledWorld(
            customers=rebuilt_customers,
            packages=rebuilt_packages,
            routes=rebuilt_routes,
            counters=world.counters,
            truck_bindings=truck_bindings,
        )

    def _link_packages_to_routes(
        self,
        snapshots: tuple[RouteSnapshot, ...],
        rebuilt_packages: Mapping[int, DeliveryPackage],
        rebuilt_routes: Mapping[int, DeliveryRoute],
    ) -> None:
        for snapshot in snapshots:
            route = rebuilt_routes[snapshot.route_id]

            for package_id in snapshot.package_ids:
                package = rebuilt_packages[package_id]
                route.restore_package_link(package)

    def _link_candidate_trucks_to_routes(
        self,
        *,
        route_snapshots: tuple[RouteSnapshot, ...],
        rebuilt_routes: Mapping[int, DeliveryRoute],
        candidate_trucks_by_id: dict[int, CandidateTruckLink],
    ) -> dict[int, CandidateTruckLink]:
        real_trucks_by_id = {truck.vehicle_id: truck for truck in self._vehicle_manager.list_fleet()}
        links_by_route_id: dict[int, CandidateTruckLink] = {}

        for snapshot in route_snapshots:
            truck_vehicle_id = snapshot.truck_vehicle_id
            if truck_vehicle_id is None:
                continue

            link = candidate_trucks_by_id.get(truck_vehicle_id)
            if link is None:
                real_truck = real_trucks_by_id[truck_vehicle_id]
                candidate_truck = self._clone_truck(real_truck)
                link = CandidateTruckLink(real_truck=real_truck, candidate_truck=candidate_truck)
                candidate_trucks_by_id[truck_vehicle_id] = link

            route = rebuilt_routes[snapshot.route_id]
            link.candidate_truck.assign(route)
            route.truck = link.candidate_truck

            links_by_route_id[snapshot.route_id] = link

        return links_by_route_id

    def _reconcile_candidate_world(
        self,
        *,
        route_snapshots: tuple[RouteSnapshot, ...],
        truck_snapshots: tuple[TruckSnapshot, ...],
        routes: Mapping[int, DeliveryRoute],
    ) -> tuple[TruckBinding, ...]:
        candidate_trucks_by_id = self._build_candidate_trucks(truck_snapshots)

        trucks_by_route_id = self._link_candidate_trucks_to_routes(
            route_snapshots=route_snapshots,
            rebuilt_routes=routes,
            candidate_trucks_by_id=candidate_trucks_by_id,
        )

        self._reconciler.reconcile_routes(
            routes=list(routes.values()),
            update_trucks=True,
        )

        return self._build_truck_bindings(
            route_snapshots=route_snapshots,
            routes=routes,
            trucks_by_route_id=trucks_by_route_id,
            candidate_trucks_by_id=candidate_trucks_by_id,
        )

    def _build_candidate_trucks(
        self,
        snapshots: tuple[TruckSnapshot, ...],
    ) -> dict[int, CandidateTruckLink]:
        real_trucks_by_id = {truck.vehicle_id: truck for truck in self._vehicle_manager.list_fleet()}
        candidates: dict[int, CandidateTruckLink] = {}

        for snapshot in snapshots:
            real_truck = real_trucks_by_id[snapshot.vehicle_id]
            candidate_truck = self._clone_truck(real_truck)

            candidate_truck.status = snapshot.status
            candidate_truck.current_location = snapshot.current_location
            candidate_truck.busy_from = dt_from_str(snapshot.busy_from)
            candidate_truck.busy_until = dt_from_str(snapshot.busy_until)
            candidate_truck.in_transit_to = snapshot.in_transit_to
            candidate_truck.route = None

            candidates[snapshot.vehicle_id] = CandidateTruckLink(
                real_truck=real_truck,
                candidate_truck=candidate_truck,
            )

        return candidates

    def _build_truck_bindings(
        self,
        *,
        route_snapshots: tuple[RouteSnapshot, ...],
        routes: Mapping[int, DeliveryRoute],
        trucks_by_route_id: dict[int, CandidateTruckLink],
        candidate_trucks_by_id: dict[int, CandidateTruckLink],
    ) -> tuple[TruckBinding, ...]:
        bindings_by_truck_id: dict[int, TruckBinding] = {}

        for truck_id, link in candidate_trucks_by_id.items():
            candidate_truck = link.candidate_truck
            bindings_by_truck_id[truck_id] = TruckBinding(
                truck=link.real_truck,
                route=candidate_truck.route,
                status=candidate_truck.status,
                current_location=candidate_truck.current_location,
                busy_from=candidate_truck.busy_from,
                busy_until=candidate_truck.busy_until,
                in_transit_to=candidate_truck.in_transit_to,
            )

        for snapshot in route_snapshots:
            truck_vehicle_id = snapshot.truck_vehicle_id
            if truck_vehicle_id is None:
                continue

            link = trucks_by_route_id[snapshot.route_id]
            candidate_truck = link.candidate_truck
            route = routes[snapshot.route_id]
            bound_route = route if route.truck is candidate_truck else None

            bindings_by_truck_id[truck_vehicle_id] = TruckBinding(
                truck=link.real_truck,
                route=bound_route,
                status=candidate_truck.status,
                current_location=candidate_truck.current_location,
                busy_from=candidate_truck.busy_from,
                busy_until=candidate_truck.busy_until,
                in_transit_to=candidate_truck.in_transit_to,
            )

        return tuple(bindings_by_truck_id[truck_id] for truck_id in sorted(bindings_by_truck_id))

    @staticmethod
    def _clone_truck(truck: Truck) -> Truck:
        clone = Truck(
            vehicle_id=truck.vehicle_id,
            name=truck.name,
            capacity=truck.capacity,
            max_range=truck.max_range,
        )
        clone.status = truck.status
        clone.current_location = truck.current_location
        clone.busy_from = truck.busy_from
        clone.busy_until = truck.busy_until
        clone.in_transit_to = truck.in_transit_to
        return clone

    def _swap_runtime_state(self, world: ReconciledWorld) -> None:
        self._runtime_state.replace_world_state(
            customers_by_id=world.customers,
            packages_by_id=world.packages,
            routes_by_id=world.routes,
            counters=world.counters,
            truck_bindings=world.truck_bindings,
        )
