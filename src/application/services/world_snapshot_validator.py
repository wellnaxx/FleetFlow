import itertools
from collections.abc import Collection

from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    TruckSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.map import Map
from src.domain.value_objects.location_code import LocationCode
from src.ports.output.vehicle_manager import VehicleManagerPort


class WorldStateSnapshotValidator:
    def __init__(self, vehicle_manager: VehicleManagerPort) -> None:
        self._vehicle_manager = vehicle_manager

    def validate_snapshot(
        self, snapshot: WorldStateSnapshot, supported_schema_versions: Collection[int]
    ) -> None:
        world = snapshot.world

        fleet = self._vehicle_manager.list_fleet()
        fleet_by_id = {truck.vehicle_id: truck for truck in fleet}

        self._validate_schema(snapshot, supported_schema_versions)
        self._validate_counters(world.counters)
        self._validate_ids(world)
        self._validate_references(world, fleet_by_id)
        self._validate_truck_snapshots(world, schema_version=snapshot.schema_version, fleet_by_id=fleet_by_id)
        self._validate_route_package_consistency(world)
        self._validate_route_package_compatibility(world)
        self._validate_truck_route_compatibility(world, fleet_by_id)
        self._validate_customer_uniqueness(world.customers)
        self._validate_counter_bounds(world)

    def _validate_schema(
        self, snapshot: WorldStateSnapshot, supported_schema_versions: Collection[int]
    ) -> None:
        if snapshot.schema_version not in supported_schema_versions:
            raise WorldStateCorruptionError(
                f"Unsupported schema version: {snapshot.schema_version}",
                reason=WorldStateCorruptionReason.UNSUPPORTED_SCHEMA,
            )

        if snapshot.schema_version == 1 and snapshot.world.trucks:
            raise WorldStateCorruptionError(
                "Schema v1 snapshots do not support truck runtime state.",
                reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
            )

    def _validate_counters(self, counters: CountersSnapshot) -> None:
        if counters.next_customer_id < 1:
            raise WorldStateCorruptionError(
                "Invalid next_customer_id in snapshot.", reason=WorldStateCorruptionReason.INVARIANT_VIOLATION
            )

        if counters.next_package_id < 1:
            raise WorldStateCorruptionError(
                "Invalid next_package_id in snapshot.", reason=WorldStateCorruptionReason.INVARIANT_VIOLATION
            )
        if counters.next_route_id < 1:
            raise WorldStateCorruptionError(
                "Invalid next_route_id in snapshot.", reason=WorldStateCorruptionReason.INVARIANT_VIOLATION
            )

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
                raise WorldStateCorruptionError(
                    f"Route {route.route_id} must contain at least two locations.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )
            self._ensure_unique_ids(route.package_ids, f"package ids for route {route.route_id}")

    def _ensure_unique_ids(self, ids: tuple[int, ...] | list[int], label: str) -> None:
        seen: set[int] = set()
        duplicates: set[int] = set()

        for item_id in ids:
            if item_id < 1:
                raise WorldStateCorruptionError(
                    f"Invalid {label} id in snapshot: {item_id}",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )
            if item_id in seen:
                duplicates.add(item_id)
            seen.add(item_id)

        if duplicates:
            dupes = ", ".join(str(item_id) for item_id in sorted(duplicates))
            raise WorldStateCorruptionError(
                f"Duplicate {label} ids in snapshot: {dupes}",
                reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
            )

    def _validate_references(self, world: WorldSnapshotData, fleet_by_id: dict[int, Truck]) -> None:
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

    def _validate_truck_snapshots(
        self, world: WorldSnapshotData, *, schema_version: int, fleet_by_id: dict[int, Truck]
    ) -> None:
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

    def _validate_route_package_consistency(self, world: WorldSnapshotData) -> None:
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

    def _validate_truck_route_compatibility(
        self, world: WorldSnapshotData, fleet_by_id: dict[int, Truck]
    ) -> None:
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

    def _validate_customer_uniqueness(self, customers: tuple[CustomerSnapshot, ...]) -> None:
        seen_emails: dict[str, int] = {}
        seen_phones: dict[str, int] = {}

        for customer in customers:
            email = customer.email.strip().lower() if customer.email else ""
            phone = customer.phone.strip() if customer.phone else ""

            if email:
                if email in seen_emails:
                    raise WorldStateCorruptionError(
                        f"Duplicate customer email in snapshot: {customer.email!r} "
                        f"used by customers {seen_emails[email]} and {customer.customer_id}.",
                        reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                    )
                seen_emails[email] = customer.customer_id

            if phone:
                if phone in seen_phones:
                    raise WorldStateCorruptionError(
                        f"Duplicate customer phone in snapshot: {customer.phone!r} "
                        f"used by customers {seen_phones[phone]} and {customer.customer_id}.",
                        reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
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
            raise WorldStateCorruptionError(
                f"Invalid next_{label}_id in snapshot: {next_id} must be greater than existing {label} ids.",
                reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
            )

    def _validate_route_package_compatibility(self, world: WorldSnapshotData) -> None:
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
