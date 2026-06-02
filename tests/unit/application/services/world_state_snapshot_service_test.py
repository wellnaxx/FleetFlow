import unittest
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import cast
from unittest.mock import patch

from src.adapters.driven.persistence.json.serialization import dt_to_str
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.truck_repository import InMemoryTruckRepository
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
from src.application.services.world_snapshot_validator import WorldStateSnapshotValidator
from src.application.services.world_state_linker import WorldStateSnapshotLinker
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder
from src.application.services.world_state_snapshot_preparer import WorldStateSnapshotPreparer
from src.application.services.world_state_snapshot_rebuilder import WorldStateSnapshotRebuilder
from src.application.services.world_state_snapshot_service import WorldStateSnapshotService
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.vehicle_manager import VehicleManager
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode, location_code_or_none
from src.ports.output.world_state_runtime_port import WorldStateRuntimePort


def _distance(_start: str, _end: str) -> int:
    return 100


def _valid_location_except_moon(code: object) -> bool:
    return code != LocationCode("MOON")


def customer_snapshot(
    customer_id: int = 1,
    *,
    name: str = "Alice",
    email: str = "",
    phone: str = "",
) -> CustomerSnapshot:
    return CustomerSnapshot(customer_id=customer_id, name=name, email=email, phone=phone)


def package_snapshot(
    package_id: int = 1,
    *,
    start: str | LocationCode = "A",
    end: str | LocationCode = "B",
    weight: float = 5.0,
    customer_id: int = 1,
    route_id: int | None = None,
) -> PackageSnapshot:
    return PackageSnapshot(
        package_id=package_id,
        start=LocationCode(start),
        end=LocationCode(end),
        weight=weight,
        customer_id=customer_id,
        route_id=route_id,
    )


def route_snapshot(
    route_id: int = 1,
    *,
    locations: tuple[str | LocationCode, ...] = ("A", "B"),
    departure_time: str | None = None,
    truck_vehicle_id: int | None = None,
    package_ids: tuple[int, ...] = (),
) -> RouteSnapshot:
    return RouteSnapshot(
        route_id=route_id,
        locations=tuple(LocationCode(location) for location in locations),
        departure_time=departure_time,
        truck_vehicle_id=truck_vehicle_id,
        package_ids=package_ids,
    )


def truck_snapshot(
    vehicle_id: int = 1001,
    *,
    status: TruckStatus = TruckStatus.FREE,
    current_location: str | LocationCode | None = "A",
    route_id: int | None = None,
    busy_from: str | None = None,
    busy_until: str | None = None,
    in_transit_to: str | LocationCode | None = None,
) -> TruckSnapshot:
    return TruckSnapshot(
        vehicle_id=vehicle_id,
        status=status,
        current_location=location_code_or_none(current_location),
        route_id=route_id,
        busy_from=busy_from,
        busy_until=busy_until,
        in_transit_to=location_code_or_none(in_transit_to),
    )


class _RuntimeStateAdapter(WorldStateRuntimePort):
    def __init__(
        self,
        customer_repo: InMemoryCustomerRepository,
        package_repo: InMemoryPackageRepository,
        route_repo: InMemoryRouteRepository,
        vehicle_manager: VehicleManager,
    ) -> None:
        self._customer_repo = customer_repo
        self._package_repo = package_repo
        self._route_repo = route_repo
        self._vehicle_manager = vehicle_manager

    def replace_world_state(
        self,
        *,
        customers_by_id: Mapping[int, Customer],
        packages_by_id: Mapping[int, DeliveryPackage],
        routes_by_id: Mapping[int, DeliveryRoute],
        counters: CountersSnapshot,
        truck_bindings: Sequence[TruckBinding],
    ) -> None:
        self._customer_repo.replace_customers(customers_by_id, counters.next_customer_id)
        self._package_repo.replace_packages(packages_by_id, counters.next_package_id)
        self._route_repo.replace_routes(routes_by_id, counters.next_route_id)
        self._vehicle_manager.replace_truck_bindings(truck_bindings)


class WorldStateSnapshotServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.route_map_locations = patch(
            "src.domain.entities.delivery_route.Map.get_locations",
            return_value=[LocationCode("A"), LocationCode("B"), LocationCode("C")],
        )
        self.route_map_distance = patch(
            "src.domain.entities.delivery_route.Map.get_distance",
            side_effect=_distance,
        )
        self.package_map_valid = patch(
            "src.domain.entities.delivery_package.Map.is_valid_location",
            return_value=True,
        )
        self.vehicle_map_locations = patch(
            "src.composition.seed_fleet.Map.get_locations",
            return_value=[LocationCode("A"), LocationCode("B"), LocationCode("C")],
        )

        self.route_map_locations.start()
        self.route_map_distance.start()
        self.package_map_valid.start()
        self.vehicle_map_locations.start()
        self.addCleanup(self.route_map_locations.stop)
        self.addCleanup(self.route_map_distance.stop)
        self.addCleanup(self.package_map_valid.stop)
        self.addCleanup(self.vehicle_map_locations.stop)

        self.customer_repo = InMemoryCustomerRepository()
        self.package_repo = InMemoryPackageRepository()
        self.route_repo = InMemoryRouteRepository()
        self.truck_repo = InMemoryTruckRepository()
        self.vehicle_manager = VehicleManager(self.truck_repo)
        self.runtime_state = _RuntimeStateAdapter(
            self.customer_repo,
            self.package_repo,
            self.route_repo,
            self.vehicle_manager,
        )
        self.reconciler = WorldStateReconciliationService()
        self.builder = WorldStateSnapshotBuilder()
        self.validator = WorldStateSnapshotValidator(vehicle_manager=self.vehicle_manager)
        self.rebuilder = WorldStateSnapshotRebuilder()
        self.linker = WorldStateSnapshotLinker(vehicle_manager=self.vehicle_manager)
        self.preparer = WorldStateSnapshotPreparer(
            reconciler=self.reconciler,
            validator=self.validator,
            rebuilder=self.rebuilder,
            linker=self.linker,
        )
        self.service = WorldStateSnapshotService(
            customer_repo=self.customer_repo,
            package_repo=self.package_repo,
            route_repo=self.route_repo,
            vehicle_manager=self.vehicle_manager,
            runtime_state=self.runtime_state,
            builder=self.builder,
            preparer=self.preparer,
        )

    def make_snapshot(
        self,
        *,
        schema_version: int = 2,
        counters: CountersSnapshot | None = None,
        customers: tuple[CustomerSnapshot, ...] | None = None,
        packages: tuple[PackageSnapshot, ...] | None = None,
        routes: tuple[RouteSnapshot, ...] | None = None,
        trucks: tuple[TruckSnapshot, ...] | None = None,
    ) -> WorldStateSnapshot:
        resolved_routes = routes or ()
        if trucks is None and schema_version == 2:
            resolved_trucks = self.fleet_truck_snapshots_for_routes(resolved_routes)
        else:
            resolved_trucks = trucks or ()

        return WorldStateSnapshot(
            schema_version=schema_version,
            world=WorldSnapshotData(
                counters=counters or CountersSnapshot(2, 2, 2),
                customers=customers or (),
                packages=packages or (),
                routes=resolved_routes,
                trucks=resolved_trucks,
            ),
        )

    def fleet_truck_snapshots_for_routes(
        self,
        routes: tuple[RouteSnapshot, ...] = (),
        *overrides: TruckSnapshot,
    ) -> tuple[TruckSnapshot, ...]:
        overrides_by_id = {snapshot.vehicle_id: snapshot for snapshot in overrides}
        routes_by_truck_id = {
            route.truck_vehicle_id: route for route in routes if route.truck_vehicle_id is not None
        }

        snapshots: list[TruckSnapshot] = []
        for truck in self.vehicle_manager.list_fleet():
            override = overrides_by_id.get(truck.vehicle_id)
            if override is not None:
                snapshots.append(override)
                continue

            assigned_route = routes_by_truck_id.get(truck.vehicle_id)
            if assigned_route is not None:
                snapshots.append(
                    truck_snapshot(
                        vehicle_id=truck.vehicle_id,
                        status=TruckStatus.ON_THE_WAY,
                        current_location=assigned_route.locations[0],
                        route_id=assigned_route.route_id,
                        busy_from=assigned_route.departure_time,
                    )
                )
                continue

            snapshots.append(
                truck_snapshot(
                    vehicle_id=truck.vehicle_id,
                    current_location=truck.current_location,
                )
            )

        return tuple(snapshots)

    def assert_corrupt(self, snapshot: WorldStateSnapshot, message: str) -> None:
        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn(message, str(ctx.exception))

    def test_build_snapshot_serializes_sorted_runtime_state(self) -> None:
        customer_b = Customer(
            customer_id=2,
            contact=ContactInfo(name="Bobby", email="bob@example.com", phone_number="0412345678"),
        )
        customer_a = Customer(
            customer_id=1,
            contact=ContactInfo(name="Alice", email="alice@example.com", phone_number="0498765432"),
        )
        self.customer_repo.add(customer_b)
        self.customer_repo.add(customer_a)

        package_b = DeliveryPackage(
            package_id=7,
            start_location=LocationCode("B"),
            end_location=LocationCode("C"),
            weight=7.0,
            customer=customer_b,
        )
        package_a = DeliveryPackage(
            package_id=3,
            start_location=LocationCode("A"),
            end_location=LocationCode("B"),
            weight=3.5,
            customer=customer_a,
        )
        customer_b.add_package(package_b)
        customer_a.add_package(package_a)
        self.package_repo.add(package_b)
        self.package_repo.add(package_a)

        departure_time = datetime(2099, 1, 1, 10, 0, 0)
        route = DeliveryRoute(
            LocationCode("A"), LocationCode("B"), LocationCode("C"), departure_time=departure_time, route_id=5
        )
        route.assign_package(package_b)
        route.assign_package(package_a)
        self.route_repo.add(route)

        truck = self.vehicle_manager.find_by_id(1002)
        assert truck is not None
        truck.assign(route)
        route.truck = truck

        snapshot = self.service.build_snapshot()

        self.assertEqual(snapshot.schema_version, 2)
        self.assertEqual(snapshot.world.counters, CountersSnapshot(3, 8, 6))
        self.assertEqual(
            snapshot.world.customers,
            (
                CustomerSnapshot(customer_id=1, name="Alice", email="alice@example.com", phone="0498765432"),
                CustomerSnapshot(customer_id=2, name="Bobby", email="bob@example.com", phone="0412345678"),
            ),
        )
        self.assertEqual(
            snapshot.world.packages,
            (
                PackageSnapshot(
                    package_id=3,
                    start=LocationCode("A"),
                    end=LocationCode("B"),
                    weight=3.5,
                    customer_id=1,
                    route_id=5,
                ),
                PackageSnapshot(
                    package_id=7,
                    start=LocationCode("B"),
                    end=LocationCode("C"),
                    weight=7.0,
                    customer_id=2,
                    route_id=5,
                ),
            ),
        )
        self.assertEqual(
            snapshot.world.routes,
            (
                RouteSnapshot(
                    route_id=5,
                    locations=(LocationCode("A"), LocationCode("B"), LocationCode("C")),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1002,
                    package_ids=(3, 7),
                ),
            ),
        )

    def test_build_snapshot_preserves_partial_package_route_id(self) -> None:
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        package = DeliveryPackage(
            package_id=3,
            start_location=LocationCode("A"),
            end_location=LocationCode("B"),
            weight=3.5,
            customer=customer,
            route_id=5,
        )
        customer.add_package(package)
        self.customer_repo.add(customer)
        self.package_repo.add(package)

        snapshot = self.service.build_snapshot()

        self.assertEqual(snapshot.world.packages[0].route_id, 5)

    def test_build_snapshot_serializes_truck_runtime_state(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None

        truck.status = TruckStatus.FREE
        truck.current_location = LocationCode("B")
        truck.busy_from = None
        truck.busy_until = None
        truck.in_transit_to = None
        truck.route = None

        snapshot = self.service.build_snapshot()

        truck_snapshot = next(
            truck_snapshot for truck_snapshot in snapshot.world.trucks if truck_snapshot.vehicle_id == 1001
        )

        self.assertEqual(truck_snapshot.status, TruckStatus.FREE)
        self.assertEqual(truck_snapshot.current_location, "B")
        self.assertIsNone(truck_snapshot.route_id)
        self.assertIsNone(truck_snapshot.busy_from)
        self.assertIsNone(truck_snapshot.busy_until)
        self.assertIsNone(truck_snapshot.in_transit_to)

    def test_apply_snapshot_rejects_unsupported_schema_version(self) -> None:
        snapshot = self.make_snapshot(schema_version=99)

        self.assert_corrupt(snapshot, "Unsupported schema version")

    def test_apply_snapshot_accepts_legacy_v1_schema_version(self) -> None:
        snapshot = self.make_snapshot(
            schema_version=1,
            counters=CountersSnapshot(1, 1, 2),
            routes=(route_snapshot(),),
        )

        self.service.apply_snapshot(snapshot)

        self.assertIsNotNone(self.route_repo.get_by_id(1))

    def test_apply_snapshot_rejects_legacy_v1_schema_with_truck_snapshots(self) -> None:
        snapshot = self.make_snapshot(
            schema_version=1,
            counters=CountersSnapshot(1, 1, 1),
            trucks=(truck_snapshot(),),
        )

        self.assert_corrupt(snapshot, "Schema v1 snapshots do not support truck runtime state")

    def test_apply_snapshot_rejects_v2_snapshot_missing_fleet_truck_snapshots(self) -> None:
        snapshot = self.make_snapshot(
            schema_version=2,
            counters=CountersSnapshot(1, 1, 1),
            trucks=(),
        )

        self.assert_corrupt(snapshot, "Schema v2 snapshot is missing truck snapshots")

    def test_apply_snapshot_rejects_invalid_counter_values(self) -> None:
        invalid_counters = (
            ("customer", CountersSnapshot(0, 2, 2), "next_customer_id"),
            ("package", CountersSnapshot(2, 0, 2), "next_package_id"),
            ("route", CountersSnapshot(2, 2, 0), "next_route_id"),
        )

        for label, counters, message in invalid_counters:
            with self.subTest(label=label):
                snapshot = self.make_snapshot(counters=counters)

                self.assert_corrupt(snapshot, message)

    def test_apply_snapshot_rejects_duplicate_top_level_ids(self) -> None:
        duplicate_cases = (
            (
                "customer",
                self.make_snapshot(
                    customers=(
                        customer_snapshot(),
                        customer_snapshot(name="Bobby"),
                    )
                ),
                "Duplicate customer ids",
            ),
            (
                "package",
                self.make_snapshot(
                    customers=(customer_snapshot(),),
                    packages=(
                        package_snapshot(weight=1.0),
                        package_snapshot(start="B", end="C", weight=2.0),
                    ),
                ),
                "Duplicate package ids",
            ),
            (
                "route",
                self.make_snapshot(
                    routes=(
                        route_snapshot(),
                        route_snapshot(locations=("B", "C")),
                    )
                ),
                "Duplicate route ids",
            ),
        )

        for label, snapshot, message in duplicate_cases:
            with self.subTest(label=label):
                self.assert_corrupt(snapshot, message)

    def test_apply_snapshot_rejects_duplicate_package_ids_within_route(self) -> None:
        snapshot = self.make_snapshot(
            customers=(customer_snapshot(),),
            packages=(package_snapshot(route_id=1),),
            routes=(route_snapshot(package_ids=(1, 1)),),
        )

        self.assert_corrupt(snapshot, "Duplicate package ids for route 1")

    def test_apply_snapshot_rejects_duplicate_customer_email_after_normalization(self) -> None:
        snapshot = self.make_snapshot(
            customers=(
                customer_snapshot(email=" Alice@Example.com "),
                customer_snapshot(customer_id=2, name="Bobby", email="alice@example.com"),
            ),
        )

        self.assert_corrupt(snapshot, "Duplicate customer email")

    def test_apply_snapshot_rejects_duplicate_customer_phone_after_trimming(self) -> None:
        snapshot = self.make_snapshot(
            customers=(
                customer_snapshot(phone=" 0412345678 "),
                customer_snapshot(customer_id=2, name="Bobby", phone="0412345678"),
            ),
        )

        self.assert_corrupt(snapshot, "Duplicate customer phone")

    def test_apply_snapshot_allows_empty_and_missing_customer_contact_values(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(3, 1, 1),
            customers=(
                customer_snapshot(email=cast(str, None), phone=cast(str, None)),
                customer_snapshot(customer_id=2, name="Bobby", email="", phone=""),
            ),
        )

        self.service.apply_snapshot(snapshot)

        first_customer = self.customer_repo.get_by_id(1)
        second_customer = self.customer_repo.get_by_id(2)

        assert first_customer is not None
        assert second_customer is not None
        self.assertEqual(first_customer.contact.email, "")
        self.assertEqual(first_customer.contact.phone_number, "")
        self.assertEqual(second_customer.contact.email, "")
        self.assertEqual(second_customer.contact.phone_number, "")

    def test_apply_snapshot_rejects_missing_references(self) -> None:
        missing_reference_cases = (
            (
                "missing customer",
                self.make_snapshot(packages=(package_snapshot(customer_id=99),)),
                "references missing customer 99",
            ),
            (
                "missing route",
                self.make_snapshot(
                    customers=(customer_snapshot(),),
                    packages=(package_snapshot(route_id=99),),
                ),
                "references missing route 99",
            ),
            (
                "missing package",
                self.make_snapshot(routes=(route_snapshot(package_ids=(99,)),)),
                "references missing package 99",
            ),
            (
                "missing truck",
                self.make_snapshot(routes=(route_snapshot(truck_vehicle_id=9999),)),
                "references missing truck 9999",
            ),
        )

        for label, snapshot, message in missing_reference_cases:
            with self.subTest(label=label):
                self.assert_corrupt(snapshot, message)

    def test_apply_snapshot_rejects_package_route_forward_inconsistency(self) -> None:
        snapshot = self.make_snapshot(
            customers=(customer_snapshot(),),
            packages=(package_snapshot(route_id=1),),
            routes=(route_snapshot(),),
        )

        self.assert_corrupt(snapshot, "does not include that package")

    def test_apply_snapshot_restores_customer_package_backrefs(self) -> None:
        snapshot = self.make_snapshot(
            customers=(customer_snapshot(),),
            packages=(package_snapshot(route_id=1),),
            routes=(route_snapshot(package_ids=(1,)),),
        )

        self.service.apply_snapshot(snapshot)

        customer = self.customer_repo.get_by_id(1)
        package = self.package_repo.get_by_id(1)
        route = self.route_repo.get_by_id(1)

        assert customer is not None
        assert package is not None
        assert route is not None
        self.assertEqual(tuple(customer.delivery_packages), (package,))
        self.assertIs(package.customer, customer)
        self.assertIs(package.route, route)
        self.assertEqual(route.packages, (package,))

    def test_apply_snapshot_restores_truck_assignment_state(self) -> None:
        departure_time = datetime(2099, 1, 1, 10, 0, 0)
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                route_snapshot(
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                ),
            ),
        )

        self.service.apply_snapshot(snapshot)

        route = self.route_repo.get_by_id(1)
        truck = self.vehicle_manager.find_by_id(1001)

        assert route is not None
        assert truck is not None
        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(truck.busy_from, departure_time)
        self.assertEqual(truck.busy_until, route.eta_final)
        self.assertIsNone(truck.in_transit_to)

    def test_apply_snapshot_reconciles_completed_truck_before_swap(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                route_snapshot(
                    departure_time=dt_to_str(datetime(2025, 1, 1, 10, 0, 0)),
                    truck_vehicle_id=1001,
                ),
            ),
        )

        self.service.apply_snapshot(snapshot)

        route = self.route_repo.get_by_id(1)
        truck = self.vehicle_manager.find_by_id(1001)

        assert route is not None
        assert truck is not None
        self.assertIsNone(route.truck)
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertEqual(truck.current_location, "B")
        self.assertIsNone(truck.busy_from)
        self.assertIsNone(truck.busy_until)
        self.assertIsNone(truck.in_transit_to)

    def test_apply_snapshot_rejects_duplicate_truck_assignments(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 3),
            routes=(
                route_snapshot(
                    truck_vehicle_id=1001,
                ),
                route_snapshot(
                    route_id=2,
                    locations=("B", "C"),
                    truck_vehicle_id=1001,
                ),
            ),
        )

        self.assert_corrupt(snapshot, "assigned to multiple routes")

    def test_apply_snapshot_rejects_route_package_reverse_inconsistency(self) -> None:
        snapshot = self.make_snapshot(
            customers=(customer_snapshot(),),
            packages=(package_snapshot(),),
            routes=(route_snapshot(package_ids=(1,)),),
        )

        self.assert_corrupt(snapshot, "includes package 1")

    def test_apply_snapshot_restores_scheduled_and_unassigned_package_state(self) -> None:
        departure_time = datetime(2025, 1, 1, 10, 0, 0)
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 3, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(
                    start="A",
                    end="C",
                    route_id=1,
                ),
                package_snapshot(
                    package_id=2,
                    start="A",
                    end="B",
                    weight=4.0,
                ),
            ),
            routes=(
                route_snapshot(
                    locations=("A", "B", "C"),
                    departure_time=dt_to_str(departure_time),
                    package_ids=(1,),
                ),
            ),
        )

        self.service.apply_snapshot(snapshot)

        customer = self.customer_repo.get_by_id(1)
        assigned_package = self.package_repo.get_by_id(1)
        unassigned_package = self.package_repo.get_by_id(2)
        route = self.route_repo.get_by_id(1)

        assert customer is not None
        assert assigned_package is not None
        assert unassigned_package is not None
        assert route is not None
        self.assertEqual(tuple(customer.delivery_packages), (assigned_package, unassigned_package))
        self.assertEqual(assigned_package.expected_arrival, route.arrival_time_at(LocationCode("C")))
        self.assertIsNone(unassigned_package.route)
        self.assertIsNone(unassigned_package.expected_arrival)

    def test_apply_snapshot_updates_repo_indexes_and_next_ids(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(4, 5, 6),
            customers=(
                customer_snapshot(
                    customer_id=3,
                    email="alice@example.com",
                    phone="0412345678",
                ),
            ),
        )

        self.service.apply_snapshot(snapshot)

        customer = self.customer_repo.get_by_id(3)

        assert customer is not None
        self.assertEqual(self.customer_repo.peek_next_id(), 4)
        self.assertEqual(self.package_repo.peek_next_id(), 5)
        self.assertEqual(self.route_repo.peek_next_id(), 6)
        self.assertIs(self.customer_repo.get_by_email("alice@example.com"), customer)
        self.assertIs(self.customer_repo.get_by_phone("0412345678"), customer)

    def test_apply_snapshot_rejects_counter_not_greater_than_existing_ids(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 5),
            routes=(
                route_snapshot(
                    route_id=5,
                ),
            ),
        )

        self.assert_corrupt(snapshot, "Invalid next_route_id in snapshot")

    def test_apply_snapshot_clears_existing_truck_bindings_when_snapshot_has_none(self) -> None:
        route = DeliveryRoute(
            LocationCode("A"), LocationCode("B"), departure_time=datetime(2025, 1, 1, 8, 0, 0), route_id=1
        )
        self.route_repo.add(route)

        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.assign(route)
        route.truck = truck

        self.service.apply_snapshot(self.make_snapshot(counters=CountersSnapshot(1, 1, 1)))

        self.assertIsNone(self.route_repo.get_by_id(1))
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertIsNone(truck.busy_from)
        self.assertIsNone(truck.busy_until)
        self.assertIsNone(truck.in_transit_to)

    def test_apply_snapshot_does_not_mutate_runtime_when_validation_fails(self) -> None:
        customer = Customer(
            customer_id=1,
            contact=ContactInfo(
                name="Alice",
                email="alice@example.com",
                phone_number="0412345678",
            ),
        )
        self.customer_repo.add(customer)

        package = DeliveryPackage(
            package_id=1,
            start_location=LocationCode("A"),
            end_location=LocationCode("B"),
            weight=5.0,
            customer=customer,
        )
        customer.add_package(package)
        self.package_repo.add(package)

        route = DeliveryRoute(
            LocationCode("A"), LocationCode("B"), departure_time=datetime(2025, 1, 1, 9, 0, 0), route_id=1
        )
        route.assign_package(package)
        self.route_repo.add(route)

        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.assign(route)
        route.truck = truck

        snapshot = self.make_snapshot(
            customers=(),
            packages=(
                package_snapshot(
                    package_id=2,
                    weight=4.0,
                    customer_id=99,
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError):
            self.service.apply_snapshot(snapshot)

        self.assertIs(self.customer_repo.get_by_id(1), customer)
        self.assertIs(self.package_repo.get_by_id(1), package)
        self.assertIs(self.route_repo.get_by_id(1), route)
        self.assertEqual(self.customer_repo.peek_next_id(), 2)
        self.assertEqual(self.package_repo.peek_next_id(), 2)
        self.assertEqual(self.route_repo.peek_next_id(), 2)
        self.assertIs(self.customer_repo.get_by_email("alice@example.com"), customer)
        self.assertIs(self.customer_repo.get_by_phone("0412345678"), customer)
        self.assertIs(truck.route, route)
        self.assertEqual(truck.status, TruckStatus.ON_THE_WAY)

    def test_apply_snapshot_rejects_assigned_package_when_start_not_on_route(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 2, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(
                    start="C",
                    route_id=1,
                ),
            ),
            routes=(
                route_snapshot(
                    package_ids=(1,),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("starts at C", str(ctx.exception))
        self.assertIn("which is not on route 1", str(ctx.exception))

    def test_apply_snapshot_rejects_assigned_package_when_end_not_on_route(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 2, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(
                    end="C",
                    route_id=1,
                ),
            ),
            routes=(
                route_snapshot(
                    package_ids=(1,),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("ends at C", str(ctx.exception))
        self.assertIn("which is not on route 1", str(ctx.exception))

    def test_apply_snapshot_rejects_assigned_package_when_route_order_is_invalid(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 2, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(
                    start="B",
                    end=LocationCode("A"),
                    route_id=1,
                ),
            ),
            routes=(
                route_snapshot(
                    locations=(LocationCode("A"), "B", "C"),
                    package_ids=(1,),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("invalid location order", str(ctx.exception))
        self.assertIn("route 1", str(ctx.exception))

    def test_apply_snapshot_rejects_bidirectionally_consistent_but_structurally_invalid_route_package_link(
        self,
    ) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 2, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(
                    start="C",
                    end=LocationCode("A"),
                    route_id=1,
                ),
            ),
            routes=(
                route_snapshot(
                    package_ids=(1,),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("Package 1", str(ctx.exception))

    def test_apply_snapshot_does_not_mutate_runtime_when_route_package_compatibility_fails(self) -> None:
        existing_customer = Customer(
            customer_id=1,
            contact=ContactInfo(
                name="Existing",
                email="existing@example.com",
                phone_number="0412345678",
            ),
        )
        self.customer_repo.add(existing_customer)

        existing_package = DeliveryPackage(
            package_id=1,
            start_location=LocationCode("A"),
            end_location=LocationCode("B"),
            weight=5.0,
            customer=existing_customer,
        )
        existing_customer.add_package(existing_package)
        self.package_repo.add(existing_package)

        existing_route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            departure_time=datetime(2025, 1, 1, 9, 0, 0),
            route_id=1,
        )
        existing_route.assign_package(existing_package)
        self.route_repo.add(existing_route)

        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.assign(existing_route)
        existing_route.truck = truck

        invalid_snapshot = self.make_snapshot(
            counters=CountersSnapshot(3, 3, 3),
            customers=(customer_snapshot(customer_id=2, name="New"),),
            packages=(
                package_snapshot(
                    package_id=2,
                    start="C",
                    end=LocationCode("A"),
                    weight=4.0,
                    customer_id=2,
                    route_id=2,
                ),
            ),
            routes=(
                route_snapshot(
                    route_id=2,
                    package_ids=(2,),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError):
            self.service.apply_snapshot(invalid_snapshot)

        self.assertIs(self.customer_repo.get_by_id(1), existing_customer)
        self.assertIsNone(self.customer_repo.get_by_id(2))

        self.assertIs(self.package_repo.get_by_id(1), existing_package)
        self.assertIsNone(self.package_repo.get_by_id(2))

        self.assertIs(self.route_repo.get_by_id(1), existing_route)
        self.assertIsNone(self.route_repo.get_by_id(2))

        self.assertEqual(self.customer_repo.peek_next_id(), 2)
        self.assertEqual(self.package_repo.peek_next_id(), 2)
        self.assertEqual(self.route_repo.peek_next_id(), 2)

        self.assertIs(existing_package.route, existing_route)
        self.assertEqual(existing_route.packages, (existing_package,))
        self.assertIs(truck.route, existing_route)
        self.assertEqual(truck.status, TruckStatus.ON_THE_WAY)

    def test_apply_snapshot_wraps_candidate_reconciliation_failure_as_corruption(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                route_snapshot(
                    departure_time=dt_to_str(datetime(2099, 1, 1, 10, 0, 0)),
                ),
            ),
        )

        with (
            patch.object(
                self.reconciler,
                "reconcile_routes",
                side_effect=ValueError("candidate graph is invalid"),
            ),
            self.assertRaises(WorldStateCorruptionError) as ctx,
        ):
            self.service.apply_snapshot(snapshot)

        self.assertIn("candidate graph is invalid", str(ctx.exception))
        self.assertIsNone(self.route_repo.get_by_id(1))

    def test_apply_snapshot_does_not_wrap_runtime_swap_failure_as_corruption(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(route_snapshot(),),
        )

        with (
            patch.object(
                self.runtime_state,
                "replace_world_state",
                side_effect=RuntimeError("swap exploded"),
            ),
            self.assertRaises(RuntimeError) as ctx,
        ):
            self.service.apply_snapshot(snapshot)

        self.assertNotIsInstance(ctx.exception, WorldStateCorruptionError)
        self.assertIn("swap exploded", str(ctx.exception))

    def test_apply_snapshot_rejects_truck_assignment_to_unscheduled_route(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                route_snapshot(
                    truck_vehicle_id=1001,
                ),
            ),
        )

        self.assert_corrupt(snapshot, "has no departure time")

    def test_apply_snapshot_rejects_truck_assignment_when_package_weight_exceeds_capacity(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.capacity = 10

        departure_time = datetime(2099, 1, 1, 10, 0, 0)

        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 2, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(
                    weight=11.0,
                    route_id=1,
                ),
            ),
            routes=(
                route_snapshot(
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                    package_ids=(1,),
                ),
            ),
        )

        self.assert_corrupt(snapshot, "exceeds capacity")

    def test_apply_snapshot_allows_non_overlapping_packages_with_total_weight_over_capacity(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.capacity = 10

        departure_time = datetime(2099, 1, 1, 10, 0, 0)

        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 3, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(package_id=1, start=LocationCode("A"), end="B", weight=8.0, route_id=1),
                package_snapshot(package_id=2, start="B", end="C", weight=8.0, route_id=1),
            ),
            routes=(
                route_snapshot(
                    locations=(LocationCode("A"), "B", "C"),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                    package_ids=(1, 2),
                ),
            ),
        )

        self.service.apply_snapshot(snapshot)

        route = self.route_repo.get_by_id(1)
        assert route is not None
        self.assertEqual(route.maximum_segment_load(), 8.0)

    def test_apply_snapshot_rejects_truck_assignment_when_segment_load_exceeds_capacity(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.capacity = 10

        departure_time = datetime(2099, 1, 1, 10, 0, 0)

        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 3, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(package_id=1, start=LocationCode("A"), end="C", weight=6.0, route_id=1),
                package_snapshot(package_id=2, start="B", end="C", weight=6.0, route_id=1),
            ),
            routes=(
                route_snapshot(
                    locations=(LocationCode("A"), "B", "C"),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                    package_ids=(1, 2),
                ),
            ),
        )

        self.assert_corrupt(snapshot, "segment load 12")

    def test_apply_snapshot_uses_first_duplicate_route_location_for_segment_load_validation(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.capacity = 10

        departure_time = datetime(2099, 1, 1, 10, 0, 0)

        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 3, 2),
            customers=(customer_snapshot(),),
            packages=(
                package_snapshot(package_id=1, start="A", end="B", weight=6.0, route_id=1),
                package_snapshot(package_id=2, start="A", end="B", weight=6.0, route_id=1),
            ),
            routes=(
                route_snapshot(
                    locations=("A", "B", "A", "C"),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                    package_ids=(1, 2),
                ),
            ),
        )

        self.assert_corrupt(snapshot, "segment load 12")

    def test_apply_snapshot_rejects_truck_assignment_when_route_exceeds_range(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.max_range = 50

        departure_time = datetime(2099, 1, 1, 10, 0, 0)

        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                route_snapshot(
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                ),
            ),
        )

        self.assert_corrupt(snapshot, "exceeds range")

    def test_apply_snapshot_restores_free_truck_runtime_state(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 1),
            trucks=self.fleet_truck_snapshots_for_routes(
                (),
                truck_snapshot(
                    current_location="B",
                ),
            ),
        )

        self.service.apply_snapshot(snapshot)

        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None

        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertEqual(truck.current_location, "B")
        self.assertIsNone(truck.route)
        self.assertIsNone(truck.busy_from)
        self.assertIsNone(truck.busy_until)
        self.assertIsNone(truck.in_transit_to)

    def test_apply_snapshot_restores_in_transit_truck_runtime_state(self) -> None:
        departure_time = datetime(2025, 1, 1, 10, 0, 0)
        current_time = datetime(2025, 1, 1, 10, 30, 0)
        routes = (
            route_snapshot(
                departure_time=dt_to_str(departure_time),
                truck_vehicle_id=1001,
            ),
        )
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=routes,
            trucks=self.fleet_truck_snapshots_for_routes(
                routes,
                truck_snapshot(
                    status=TruckStatus.ON_THE_WAY,
                    current_location=LocationCode("A"),
                    route_id=1,
                    busy_from=dt_to_str(departure_time),
                    in_transit_to="B",
                ),
            ),
        )

        with patch("src.application.services.world_state_reconciliation_service.datetime") as datetime_mock:
            datetime_mock.now.return_value = current_time
            self.service.apply_snapshot(snapshot)

        route = self.route_repo.get_by_id(1)
        truck = self.vehicle_manager.find_by_id(1001)

        assert route is not None
        assert truck is not None
        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(truck.current_location, "A")
        self.assertEqual(truck.in_transit_to, "B")
        self.assertEqual(truck.busy_from, departure_time)
        self.assertEqual(truck.busy_until, route.eta_final)

    def test_completed_route_releases_truck_to_destination_and_state_round_trips(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None

        routes = (
            route_snapshot(
                departure_time=dt_to_str(datetime(2025, 1, 1, 10, 0, 0)),
                truck_vehicle_id=1001,
            ),
        )
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=routes,
            trucks=self.fleet_truck_snapshots_for_routes(
                routes,
                truck_snapshot(
                    status=TruckStatus.ON_THE_WAY,
                    current_location="A",
                    route_id=1,
                    busy_from=dt_to_str(datetime(2025, 1, 1, 10, 0, 0)),
                ),
            ),
        )

        self.service.apply_snapshot(snapshot)

        truck = self.vehicle_manager.find_by_id(1001)
        route = self.route_repo.get_by_id(1)

        assert truck is not None
        assert route is not None

        self.assertIsNone(route.truck)
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertEqual(truck.current_location, "B")

        saved = self.service.build_snapshot()
        saved_truck = next(item for item in saved.world.trucks if item.vehicle_id == 1001)

        self.assertEqual(saved_truck.status, TruckStatus.FREE)
        self.assertEqual(saved_truck.current_location, "B")
        self.assertIsNone(saved_truck.route_id)

    def test_apply_snapshot_rejects_missing_truck_snapshot_id(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 1),
            trucks=(
                truck_snapshot(
                    vehicle_id=9999,
                    current_location="A",
                ),
            ),
        )

        self.assert_corrupt(snapshot, "references missing truck 9999")

    def test_apply_snapshot_rejects_duplicate_truck_snapshot_id(self) -> None:
        truck = truck_snapshot()
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 1),
            trucks=(truck, truck),
        )

        self.assert_corrupt(snapshot, "Duplicate truck id")

    def test_apply_snapshot_rejects_invalid_truck_status(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 1),
            trucks=(
                truck_snapshot(
                    status="Teleporting",  # type: ignore[arg-type]
                ),
            ),
        )

        self.assert_corrupt(snapshot, "invalid status")

    def test_apply_snapshot_rejects_free_truck_with_route_reference(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                route_snapshot(
                    departure_time=dt_to_str(datetime(2099, 1, 1, 10, 0, 0)),
                    truck_vehicle_id=1001,
                ),
            ),
            trucks=(
                truck_snapshot(
                    status=TruckStatus.FREE,
                    route_id=1,
                ),
            ),
        )

        self.assert_corrupt(snapshot, "Free truck 1001 cannot point to route 1")

    def test_apply_snapshot_rejects_free_truck_with_busy_window(self) -> None:
        busy_window_cases = (
            ("busy_from", dt_to_str(datetime(2099, 1, 1, 10, 0, 0)), None),
            ("busy_until", None, dt_to_str(datetime(2099, 1, 1, 11, 0, 0))),
        )

        for label, busy_from, busy_until in busy_window_cases:
            with self.subTest(label=label):
                snapshot = self.make_snapshot(
                    counters=CountersSnapshot(1, 1, 1),
                    trucks=(
                        truck_snapshot(
                            status=TruckStatus.FREE,
                            busy_from=busy_from,
                            busy_until=busy_until,
                        ),
                    ),
                )

                self.assert_corrupt(snapshot, "Free truck 1001 cannot have a busy window")

    def test_apply_snapshot_rejects_free_truck_with_transit_destination(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 1),
            trucks=(
                truck_snapshot(
                    status=TruckStatus.FREE,
                    in_transit_to="B",
                ),
            ),
        )

        self.assert_corrupt(snapshot, "Free truck 1001 cannot be in transit")

    def test_apply_snapshot_rejects_on_the_way_truck_without_route_reference(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 1),
            trucks=(
                truck_snapshot(
                    status=TruckStatus.ON_THE_WAY,
                ),
            ),
        )

        self.assert_corrupt(snapshot, "On-the-way truck 1001 must point to a route")

    def test_apply_snapshot_rejects_truck_with_unsupported_current_location(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 1),
            trucks=(
                truck_snapshot(
                    current_location="MOON",
                ),
            ),
        )

        with patch(
            "src.application.services.world_snapshot_validator.Map.is_valid_location",
            side_effect=_valid_location_except_moon,
        ):
            self.assert_corrupt(snapshot, "unsupported current location MOON")

    def test_apply_snapshot_rejects_truck_with_unsupported_transit_destination(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                route_snapshot(
                    departure_time=dt_to_str(datetime(2099, 1, 1, 10, 0, 0)),
                    truck_vehicle_id=1001,
                ),
            ),
            trucks=(
                truck_snapshot(
                    status=TruckStatus.ON_THE_WAY,
                    route_id=1,
                    in_transit_to="MOON",
                ),
            ),
        )

        with patch(
            "src.application.services.world_snapshot_validator.Map.is_valid_location",
            side_effect=_valid_location_except_moon,
        ):
            self.assert_corrupt(snapshot, "unsupported transit destination MOON")

    def test_apply_snapshot_rejects_truck_snapshot_route_mismatch(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                route_snapshot(
                    departure_time=dt_to_str(datetime(2099, 1, 1, 10, 0, 0)),
                    truck_vehicle_id=1001,
                ),
            ),
            trucks=(
                truck_snapshot(
                    status=TruckStatus.ON_THE_WAY,
                    current_location="A",
                    route_id=2,
                ),
            ),
        )

        self.assert_corrupt(snapshot, "points to route 2")
