from typing import ClassVar

from src.adapters.driven.persistence.json.serialization import dt_from_str, dt_to_str
from src.application.dto.candidate_truck_dto import CandidateTruckLink
from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.value_objects.contact_info import ContactInfo
from src.ports.output.customer_repository import CustomerRepositoryPort
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.vehicle_manager import VehicleManagerPort
from src.ports.output.world_state_runtime_port import WorldStateRuntimePort


class WorldStateSnapshotService:
    SCHEMA_VERSION: ClassVar[int] = 1

    def __init__(
        self,
        customer_repo: CustomerRepositoryPort,
        package_repo: PackageRepositoryPort,
        route_repo: RouteRepositoryPort,
        vehicle_manager: VehicleManagerPort,
        runtime_state: WorldStateRuntimePort,
        reconciler: WorldStateReconciliationService,
    ) -> None:
        self._customer_repo = customer_repo
        self._package_repo = package_repo
        self._route_repo = route_repo
        self._vehicle_manager = vehicle_manager
        self._runtime_state = runtime_state
        self._reconciler = reconciler

    def build_snapshot(self) -> WorldStateSnapshot:
        counters = self._build_counters_snapshot()
        customers = self._build_customer_snapshots()
        packages = self._build_package_snapshots()
        routes = self._build_route_snapshots()

        world = WorldSnapshotData(
            counters=counters,
            customers=customers,
            packages=packages,
            routes=routes,
        )
        return WorldStateSnapshot(schema_version=self.SCHEMA_VERSION, world=world)

    def _build_counters_snapshot(self) -> CountersSnapshot:
        return CountersSnapshot(
            next_customer_id=self._customer_repo.peek_next_id(),
            next_package_id=self._package_repo.peek_next_id(),
            next_route_id=self._route_repo.peek_next_id(),
        )

    def _build_customer_snapshots(self) -> tuple[CustomerSnapshot, ...]:
        return tuple(
            CustomerSnapshot(
                customer_id=customer.customer_id,
                name=customer.name,
                email=customer.email or "",
                phone=customer.phone_number or "",
            )
            for customer in sorted(self._customer_repo.list_all(), key=lambda customer: customer.customer_id)
        )

    def _build_package_snapshots(self) -> tuple[PackageSnapshot, ...]:
        return tuple(
            PackageSnapshot(
                package_id=package.package_id,
                start=package.start_location,
                end=package.end_location,
                weight=package.weight,
                customer_id=package.customer.customer_id,
                route_id=package.route.route_id if package.route is not None else None,
            )
            for package in sorted(self._package_repo.list_all(), key=lambda package: package.package_id)
        )

    def _build_route_snapshots(self) -> tuple[RouteSnapshot, ...]:
        return tuple(
            RouteSnapshot(
                route_id=route.route_id,
                locations=tuple(route.locations),
                departure_time=dt_to_str(route.departure_time),
                truck_vehicle_id=route.truck.vehicle_id if route.truck is not None else None,
                package_ids=tuple(sorted(package.package_id for package in route.packages)),
            )
            for route in sorted(self._route_repo.list_all(), key=lambda route: route.route_id)
        )

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        world = snapshot.world

        try:
            self._validate_schema(snapshot)
            self._validate_counters(world.counters)
            self._validate_ids(world)
            self._validate_references(world)
            self._validate_route_package_consistency(world)
            self._validate_route_package_compatibility(world)
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
                snapshots=world.routes,
                routes=rebuilt_routes,
            )

        except (KeyError, TypeError, ValueError) as exc:
            raise WorldStateCorruptionError(f"Invalid world state snapshot: {exc}") from exc

        self._swap_runtime_state(
            ReconciledWorld(
                customers=rebuilt_customers,
                packages=rebuilt_packages,
                routes=rebuilt_routes,
                counters=world.counters,
                truck_bindings=truck_bindings,
            )
        )

    def _validate_schema(self, snapshot: WorldStateSnapshot) -> None:
        if snapshot.schema_version != self.SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema version: {snapshot.schema_version}")

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
        return {
            snapshot.customer_id: Customer(
                customer_id=snapshot.customer_id,
                contact=ContactInfo(
                    name=snapshot.name,
                    email=snapshot.email,
                    phone_number=snapshot.phone,
                ),
            )
            for snapshot in snapshots
        }

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
        return {
            snapshot.route_id: DeliveryRoute(
                *snapshot.locations,
                departure_time=dt_from_str(snapshot.departure_time),
                route_id=snapshot.route_id,
            )
            for snapshot in snapshots
        }

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
        self, snapshots: tuple[RouteSnapshot, ...], rebuilt_routes: dict[int, DeliveryRoute]
    ) -> dict[int, CandidateTruckLink]:
        trucks_by_id = {truck.vehicle_id: truck for truck in self._vehicle_manager.list_fleet()}

        trucks_by_route_id: dict[int, CandidateTruckLink] = {}

        for snapshot in snapshots:
            if snapshot.truck_vehicle_id is None:
                continue

            real_truck = trucks_by_id[snapshot.truck_vehicle_id]
            candidate_truck = self._clone_truck(real_truck)
            route = rebuilt_routes[snapshot.route_id]
            candidate_truck.assign(route)
            route.truck = candidate_truck

            trucks_by_route_id[snapshot.route_id] = CandidateTruckLink(real_truck, candidate_truck)

        return trucks_by_route_id

    def _reconcile_candidate_world(
        self,
        snapshots: tuple[RouteSnapshot, ...],
        routes: dict[int, DeliveryRoute],
    ) -> list[TruckBinding]:
        trucks_by_route_id = self._link_candidate_trucks_to_routes(
            snapshots=snapshots,
            rebuilt_routes=routes,
        )
        self._reconciler.reconcile_routes(
            routes=list(routes.values()),
            update_trucks=True,
        )
        return self._build_truck_bindings(
            snapshots=snapshots,
            routes=routes,
            trucks_by_route_id=trucks_by_route_id,
        )

    def _build_truck_bindings(
        self,
        *,
        snapshots: tuple[RouteSnapshot, ...],
        routes: dict[int, DeliveryRoute],
        trucks_by_route_id: dict[int, CandidateTruckLink],
    ) -> list[TruckBinding]:
        bindings: list[TruckBinding] = []

        for snapshot in snapshots:
            if snapshot.truck_vehicle_id is None:
                continue

            candidate_truck_link = trucks_by_route_id[snapshot.route_id]
            real_truck = candidate_truck_link.real_truck
            candidate_truck = candidate_truck_link.candidate_truck

            route = routes[snapshot.route_id]
            bound_route = route if route.truck is candidate_truck else None

            bindings.append(
                TruckBinding(
                    truck=real_truck,
                    route=bound_route,
                    status=candidate_truck.status,
                    current_location=candidate_truck.current_location,
                    busy_from=candidate_truck.busy_from,
                    busy_until=candidate_truck.busy_until,
                    in_transit_to=candidate_truck.in_transit_to,
                )
            )

        return bindings

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
