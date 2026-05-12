"""Build, validate, reconcile, and apply world-state snapshots."""

import itertools
from collections.abc import Callable, Iterable
from typing import ClassVar, Protocol

from src.adapters.driven.persistence.json.serialization import dt_from_str
from src.application.dto.candidate_truck_dto import CandidateTruckLink
from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    TruckSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.map import Map
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode
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
        """
        self._customer_repo = customer_repo
        self._package_repo = package_repo
        self._route_repo = route_repo
        self._vehicle_manager = vehicle_manager
        self._runtime_state = runtime_state
        self._reconciler = reconciler
        self._builder = builder or WorldStateSnapshotBuilder()

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

    @staticmethod
    def _keyed_by[T, K, V](
        items: Iterable[T], *, key: Callable[[T], K], transform: Callable[[T], V]
    ) -> dict[K, V]:
        return {key(item): transform(item) for item in items}

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

        self._validate_schema(snapshot)
        self._validate_counters(world.counters)
        self._validate_ids(world)
        self._validate_references(world)
        self._validate_truck_snapshots(world, schema_version=snapshot.schema_version)
        self._validate_route_package_consistency(world)
        self._validate_route_package_compatibility(world)
        self._validate_truck_route_compatibility(world)
        self._validate_customer_uniqueness(world.customers)
        self._validate_counter_bounds(world)

        rebuilt_customers = self._rebuild_customers(world.customers)
        rebuilt_packages = self._rebuild_packages(world.packages, rebuilt_customers)
        rebuilt_routes = self._rebuild_routes(world.routes)

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

    def _validate_schema(self, snapshot: WorldStateSnapshot) -> None:
        if snapshot.schema_version not in self.SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(f"Unsupported schema version: {snapshot.schema_version}")

        if snapshot.schema_version == 1 and snapshot.world.trucks:
            raise ValueError("Schema v1 snapshots do not support truck runtime state.")

    def _validate_counters(self, counters: CountersSnapshot) -> None:
        if counters.next_customer_id < 1:
            raise ValueError("Invalid next_customer_id in snapshot.")

        if counters.next_package_id < 1:
            raise ValueError("Invalid next_package_id in snapshot.")
        if counters.next_route_id < 1:
            raise ValueError("Invalid next_route_id in snapshot.")

    def _validate_ids(self, world: WorldSnapshotData) -> None:
        self._ensure_unique_ids(
            [customer.customer_id for customer in world.customers],
            "customer",
        )
        self._ensure_unique_ids(
            [package.package_id for package in world.packages],
            "package",
        )
        self._ensure_unique_ids(
            [route.route_id for route in world.routes],
            "route",
        )

        for route in world.routes:
            if len(route.locations) < 2:
                raise ValueError(f"Route {route.route_id} must contain at least two locations.")
            self._ensure_unique_ids(route.package_ids, f"package ids for route {route.route_id}")

    def _ensure_unique_ids(self, ids: tuple[int, ...] | list[int], label: str) -> None:
        seen: set[int] = set()
        duplicates: set[int] = set()

        for item_id in ids:
            if item_id < 1:
                raise ValueError(f"Invalid {label} id in snapshot: {item_id}")
            if item_id in seen:
                duplicates.add(item_id)
            seen.add(item_id)

        if duplicates:
            dupes = ", ".join(str(item_id) for item_id in sorted(duplicates))
            raise ValueError(f"Duplicate {label} ids in snapshot: {dupes}")

    def _validate_references(self, world: WorldSnapshotData) -> None:
        customer_ids = {customer.customer_id for customer in world.customers}
        package_ids = {package.package_id for package in world.packages}
        route_ids = {route.route_id for route in world.routes}
        truck_ids = {truck.vehicle_id for truck in self._vehicle_manager.list_fleet()}
        assigned_truck_ids: set[int] = set()

        for package in world.packages:
            if package.customer_id not in customer_ids:
                raise ValueError(
                    f"Package {package.package_id} references missing customer {package.customer_id}."
                )
            if package.route_id is not None and package.route_id not in route_ids:
                raise ValueError(f"Package {package.package_id} references missing route {package.route_id}.")

        for route in world.routes:
            for package_id in route.package_ids:
                if package_id not in package_ids:
                    raise ValueError(f"Route {route.route_id} references missing package {package_id}.")
            truck_vehicle_id = route.truck_vehicle_id
            if truck_vehicle_id is None:
                continue
            if truck_vehicle_id not in truck_ids:
                raise ValueError(f"Route {route.route_id} references missing truck {truck_vehicle_id}.")
            if truck_vehicle_id in assigned_truck_ids:
                raise ValueError(f"Truck {truck_vehicle_id} is assigned to multiple routes in snapshot.")
            assigned_truck_ids.add(truck_vehicle_id)

    def _validate_truck_snapshots(self, world: WorldSnapshotData, *, schema_version: int) -> None:
        fleet_ids = {truck.vehicle_id for truck in self._vehicle_manager.list_fleet()}
        route_trucks = {
            route.truck_vehicle_id: route.route_id
            for route in world.routes
            if route.truck_vehicle_id is not None
        }

        seen_truck_ids: set[int] = set()

        for truck in world.trucks:
            if truck.vehicle_id < 1:
                raise ValueError(f"Invalid truck id in snapshot: {truck.vehicle_id}")

            if truck.vehicle_id in seen_truck_ids:
                raise ValueError(f"Duplicate truck id in snapshot: {truck.vehicle_id}")
            seen_truck_ids.add(truck.vehicle_id)

            if truck.vehicle_id not in fleet_ids:
                raise ValueError(f"Snapshot references missing truck {truck.vehicle_id}.")

            if truck.status not in TruckStatus.values():
                raise ValueError(f"Truck {truck.vehicle_id} has invalid status {truck.status!r}.")

            status = TruckStatus(truck.status)
            self._validate_truck_snapshot_locations(truck)
            self._validate_truck_snapshot_runtime_state(truck, status)

            if truck.route_id is not None:
                expected_route_id = route_trucks.get(truck.vehicle_id)
                if expected_route_id != truck.route_id:
                    raise ValueError(
                        f"Truck {truck.vehicle_id} points to route {truck.route_id}, "
                        f"but route assignment points to {expected_route_id}."
                    )

        if schema_version == 2:
            missing_truck_ids = fleet_ids - seen_truck_ids
            if missing_truck_ids:
                missing = ", ".join(str(truck_id) for truck_id in sorted(missing_truck_ids))
                raise ValueError(f"Schema v2 snapshot is missing truck snapshots: {missing}.")

        trucks_by_snapshot_id = {truck.vehicle_id: truck for truck in world.trucks}

        for truck_vehicle_id, route_id in route_trucks.items():
            truck_snapshot = trucks_by_snapshot_id.get(truck_vehicle_id)
            if truck_snapshot is not None and truck_snapshot.route_id != route_id:
                raise ValueError(
                    f"Route {route_id} assigns truck {truck_vehicle_id}, "
                    f"but truck snapshot points to route {truck_snapshot.route_id}."
                )

    @staticmethod
    def _validate_truck_snapshot_locations(truck: TruckSnapshot) -> None:
        if truck.current_location is not None and not Map.is_valid_location(truck.current_location):
            raise ValueError(
                f"Truck {truck.vehicle_id} has unsupported current location {truck.current_location}."
            )

        if truck.in_transit_to is not None and not Map.is_valid_location(truck.in_transit_to):
            raise ValueError(
                f"Truck {truck.vehicle_id} has unsupported transit destination {truck.in_transit_to}."
            )

    @staticmethod
    def _validate_truck_snapshot_runtime_state(truck: TruckSnapshot, status: TruckStatus) -> None:
        if status == TruckStatus.FREE:
            if truck.route_id is not None:
                raise ValueError(f"Free truck {truck.vehicle_id} cannot point to route {truck.route_id}.")
            if truck.busy_from is not None or truck.busy_until is not None:
                raise ValueError(f"Free truck {truck.vehicle_id} cannot have a busy window.")
            if truck.in_transit_to is not None:
                raise ValueError(f"Free truck {truck.vehicle_id} cannot be in transit.")

        if status == TruckStatus.ON_THE_WAY and truck.route_id is None:
            raise ValueError(f"On-the-way truck {truck.vehicle_id} must point to a route.")

    def _validate_route_package_consistency(self, world: WorldSnapshotData) -> None:
        route_packages: dict[int, set[int]] = {route.route_id: set(route.package_ids) for route in world.routes}
        package_route_ids = {package.package_id: package.route_id for package in world.packages}

        for package in world.packages:
            if package.route_id is None:
                continue

            if package.package_id not in route_packages.get(package.route_id, set()):
                raise ValueError(
                    f"Package {package.package_id} points to route {package.route_id}, "
                    "but the route does not include that package."
                )

        for route in world.routes:
            for package_id in route.package_ids:
                package_route_id = package_route_ids.get(package_id)
                if package_route_id != route.route_id:
                    raise ValueError(
                        f"Route {route.route_id} includes package {package_id}, "
                        f"but the package points to route {package_route_id}."
                    )

    def _validate_truck_route_compatibility(self, world: WorldSnapshotData) -> None:
        trucks_by_id = {truck.vehicle_id: truck for truck in self._vehicle_manager.list_fleet()}
        packages_by_id = {package.package_id: package for package in world.packages}

        for route in world.routes:
            truck_vehicle_id = route.truck_vehicle_id
            if truck_vehicle_id is None:
                continue

            if route.departure_time is None:
                raise ValueError(
                    f"Route {route.route_id} assigns truck {truck_vehicle_id}, "
                    "but the route has no departure time."
                )

            truck = trucks_by_id[truck_vehicle_id]

            max_segment_load = self._route_max_segment_load(route, packages_by_id)
            if max_segment_load > truck.capacity:
                raise ValueError(
                    f"Route {route.route_id} assigns truck {truck_vehicle_id}, "
                    f"but segment load {max_segment_load} exceeds capacity {truck.capacity}."
                )

            total_distance = self._route_distance_km(route.locations)
            if total_distance > truck.max_range:
                raise ValueError(
                    f"Route {route.route_id} assigns truck {truck_vehicle_id}, "
                    f"but route distance {total_distance} exceeds range {truck.max_range}."
                )

    @staticmethod
    def _route_max_segment_load(route: RouteSnapshot, packages_by_id: dict[int, PackageSnapshot]) -> float:
        segment_loads = [0.0 for _ in range(len(route.locations) - 1)]
        location_index = {location: index for index, location in enumerate(route.locations)}

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

    def _validate_customer_uniqueness(self, customers: tuple[CustomerSnapshot, ...]) -> None:
        seen_emails: dict[str, int] = {}
        seen_phones: dict[str, int] = {}

        for customer in customers:
            email = customer.email.strip().lower()
            phone = customer.phone.strip()

            if email:
                if email in seen_emails:
                    raise ValueError(
                        f"Duplicate customer email in snapshot: {customer.email!r} "
                        f"used by customers {seen_emails[email]} and {customer.customer_id}."
                    )
                seen_emails[email] = customer.customer_id

            if phone:
                if phone in seen_phones:
                    raise ValueError(
                        f"Duplicate customer phone in snapshot: {customer.phone!r} "
                        f"used by customers {seen_phones[phone]} and {customer.customer_id}."
                    )
                seen_phones[phone] = customer.customer_id

    def _validate_counter_bounds(self, world: WorldSnapshotData) -> None:
        self._validate_next_id(
            label="customer",
            next_id=world.counters.next_customer_id,
            existing_ids=[customer.customer_id for customer in world.customers],
        )
        self._validate_next_id(
            label="package",
            next_id=world.counters.next_package_id,
            existing_ids=[package.package_id for package in world.packages],
        )
        self._validate_next_id(
            label="route",
            next_id=world.counters.next_route_id,
            existing_ids=[route.route_id for route in world.routes],
        )

    def _validate_next_id(self, *, label: str, next_id: int, existing_ids: list[int]) -> None:
        if existing_ids and next_id <= max(existing_ids):
            raise ValueError(
                f"Invalid next_{label}_id in snapshot: {next_id} must be greater than existing {label} ids."
            )

    def _rebuild_customers(self, snapshots: tuple[CustomerSnapshot, ...]) -> dict[int, Customer]:
        return self._keyed_by(
            snapshots,
            key=lambda snapshot: snapshot.customer_id,
            transform=lambda snapshot: Customer(
                customer_id=snapshot.customer_id,
                contact=ContactInfo(name=snapshot.name, email=snapshot.email, phone_number=snapshot.phone),
            ),
        )

    def _rebuild_packages(
        self, snapshots: tuple[PackageSnapshot, ...], rebuilt_customers: dict[int, Customer]
    ) -> dict[int, DeliveryPackage]:
        rebuilt_packages: dict[int, DeliveryPackage] = {}

        for snapshot in snapshots:
            package = DeliveryPackage(
                package_id=snapshot.package_id,
                start_location=snapshot.start,
                end_location=snapshot.end,
                weight=snapshot.weight,
                customer=rebuilt_customers[snapshot.customer_id],
            )
            rebuilt_packages[snapshot.package_id] = package
            rebuilt_customers[snapshot.customer_id].add_package(package)

        return rebuilt_packages

    def _rebuild_routes(self, snapshots: tuple[RouteSnapshot, ...]) -> dict[int, DeliveryRoute]:
        return self._keyed_by(
            snapshots,
            key=lambda snapshot: snapshot.route_id,
            transform=lambda snapshot: DeliveryRoute(
                *snapshot.locations,
                departure_time=dt_from_str(snapshot.departure_time),
                route_id=snapshot.route_id,
            ),
        )

    def _validate_route_package_compatibility(self, world: WorldSnapshotData) -> None:
        routes_by_id = {route.route_id: route for route in world.routes}

        for package in world.packages:
            if package.route_id is None:
                continue

            route = routes_by_id[package.route_id]
            locations = route.locations

            if package.start not in locations:
                raise ValueError(
                    f"Package {package.package_id} starts at {package.start}, "
                    f"which is not on route {route.route_id}."
                )

            if package.end not in locations:
                raise ValueError(
                    f"Package {package.package_id} ends at {package.end}, "
                    f"which is not on route {route.route_id}."
                )

            if locations.index(package.start) >= locations.index(package.end):
                raise ValueError(
                    f"Package {package.package_id} has invalid location order on route {route.route_id}."
                )

    def _link_packages_to_routes(
        self,
        snapshots: tuple[RouteSnapshot, ...],
        rebuilt_packages: dict[int, DeliveryPackage],
        rebuilt_routes: dict[int, DeliveryRoute],
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
        rebuilt_routes: dict[int, DeliveryRoute],
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
        routes: dict[int, DeliveryRoute],
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
        routes: dict[int, DeliveryRoute],
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
