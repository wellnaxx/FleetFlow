import unittest
from datetime import datetime
from unittest.mock import patch

from src.adapters.driven.persistence.json.serialization import dt_to_str
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
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
from src.application.services.world_state_snapshot_service import WorldStateSnapshotService
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.vehicle_manager import VehicleManager
from src.domain.value_objects.contact_info import ContactInfo
from src.ports.output.world_state_runtime_port import WorldStateRuntimePort


def _distance(_start: str, _end: str) -> int:
    return 100


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
        customers_by_id: dict[int, Customer],
        packages_by_id: dict[int, DeliveryPackage],
        routes_by_id: dict[int, DeliveryRoute],
        counters: CountersSnapshot,
        truck_bindings: list[TruckBinding],
    ) -> None:
        self._customer_repo.replace_customers(customers_by_id, counters.next_customer_id)
        self._package_repo.replace_packages(packages_by_id, counters.next_package_id)
        self._route_repo.replace_routes(routes_by_id, counters.next_route_id)
        self._vehicle_manager.replace_truck_bindings(truck_bindings)


class WorldStateSnapshotServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.route_map_locations = patch(
            "src.domain.entities.delivery_route.Map.get_locations",
            return_value=["A", "B", "C"],
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
            "src.domain.services.vehicle_manager.Map.get_locations",
            return_value=["A", "B", "C"],
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
        self.vehicle_manager = VehicleManager()
        self.runtime_state = _RuntimeStateAdapter(
            self.customer_repo,
            self.package_repo,
            self.route_repo,
            self.vehicle_manager,
        )
        self.service = WorldStateSnapshotService(
            customer_repo=self.customer_repo,
            package_repo=self.package_repo,
            route_repo=self.route_repo,
            vehicle_manager=self.vehicle_manager,
            runtime_state=self.runtime_state,
            reconciler=WorldStateReconciliationService(),
        )

    def make_snapshot(
        self,
        *,
        schema_version: int = 1,
        counters: CountersSnapshot | None = None,
        customers: tuple[CustomerSnapshot, ...] | None = None,
        packages: tuple[PackageSnapshot, ...] | None = None,
        routes: tuple[RouteSnapshot, ...] | None = None,
    ) -> WorldStateSnapshot:
        return WorldStateSnapshot(
            schema_version=schema_version,
            world=WorldSnapshotData(
                counters=counters or CountersSnapshot(2, 2, 2),
                customers=customers or (),
                packages=packages or (),
                routes=routes or (),
            ),
        )

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
            start_location="B",
            end_location="C",
            weight=7.0,
            customer=customer_b,
        )
        package_a = DeliveryPackage(
            package_id=3,
            start_location="A",
            end_location="B",
            weight=3.5,
            customer=customer_a,
        )
        customer_b.add_package(package_b)
        customer_a.add_package(package_a)
        self.package_repo.add(package_b)
        self.package_repo.add(package_a)

        departure_time = datetime(2099, 1, 1, 10, 0, 0)
        route = DeliveryRoute("A", "B", "C", departure_time=departure_time, route_id=5)
        route.assign_package(package_b)
        route.assign_package(package_a)
        self.route_repo.add(route)

        truck = self.vehicle_manager.find_by_id(1002)
        assert truck is not None
        truck.assign(route)
        route.truck = truck

        snapshot = self.service.build_snapshot()

        self.assertEqual(snapshot.schema_version, 1)
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
                    start="A",
                    end="B",
                    weight=3.5,
                    customer_id=1,
                    route_id=5,
                ),
                PackageSnapshot(
                    package_id=7,
                    start="B",
                    end="C",
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
                    locations=("A", "B", "C"),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1002,
                    package_ids=(3, 7),
                ),
            ),
        )

    def test_apply_snapshot_rejects_unsupported_schema_version(self) -> None:
        snapshot = self.make_snapshot(schema_version=99)

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("Unsupported schema version", str(ctx.exception))

    def test_apply_snapshot_rejects_invalid_counter_values(self) -> None:
        invalid_counters = (
            ("customer", CountersSnapshot(0, 2, 2), "next_customer_id"),
            ("package", CountersSnapshot(2, 0, 2), "next_package_id"),
            ("route", CountersSnapshot(2, 2, 0), "next_route_id"),
        )

        for label, counters, message in invalid_counters:
            with self.subTest(label=label):
                snapshot = self.make_snapshot(counters=counters)

                with self.assertRaises(WorldStateCorruptionError) as ctx:
                    self.service.apply_snapshot(snapshot)

                self.assertIn(message, str(ctx.exception))

    def test_apply_snapshot_rejects_duplicate_top_level_ids(self) -> None:
        duplicate_cases = (
            (
                "customer",
                self.make_snapshot(
                    customers=(
                        CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),
                        CustomerSnapshot(customer_id=1, name="Bobby", email="", phone=""),
                    )
                ),
                "Duplicate customer ids",
            ),
            (
                "package",
                self.make_snapshot(
                    customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
                    packages=(
                        PackageSnapshot(
                            package_id=1,
                            start="A",
                            end="B",
                            weight=1.0,
                            customer_id=1,
                            route_id=None,
                        ),
                        PackageSnapshot(
                            package_id=1,
                            start="B",
                            end="C",
                            weight=2.0,
                            customer_id=1,
                            route_id=None,
                        ),
                    ),
                ),
                "Duplicate package ids",
            ),
            (
                "route",
                self.make_snapshot(
                    routes=(
                        RouteSnapshot(
                            route_id=1,
                            locations=("A", "B"),
                            departure_time=None,
                            truck_vehicle_id=None,
                            package_ids=(),
                        ),
                        RouteSnapshot(
                            route_id=1,
                            locations=("B", "C"),
                            departure_time=None,
                            truck_vehicle_id=None,
                            package_ids=(),
                        ),
                    )
                ),
                "Duplicate route ids",
            ),
        )

        for label, snapshot, message in duplicate_cases:
            with self.subTest(label=label):
                with self.assertRaises(WorldStateCorruptionError) as ctx:
                    self.service.apply_snapshot(snapshot)

                self.assertIn(message, str(ctx.exception))

    def test_apply_snapshot_rejects_duplicate_package_ids_within_route(self) -> None:
        snapshot = self.make_snapshot(
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="A",
                    end="B",
                    weight=5.0,
                    customer_id=1,
                    route_id=1,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
                    package_ids=(1, 1),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("Duplicate package ids for route 1", str(ctx.exception))

    def test_apply_snapshot_rejects_missing_references(self) -> None:
        missing_reference_cases = (
            (
                "missing customer",
                self.make_snapshot(
                    packages=(
                        PackageSnapshot(
                            package_id=1,
                            start="A",
                            end="B",
                            weight=5.0,
                            customer_id=99,
                            route_id=None,
                        ),
                    )
                ),
                "references missing customer 99",
            ),
            (
                "missing route",
                self.make_snapshot(
                    customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
                    packages=(
                        PackageSnapshot(
                            package_id=1,
                            start="A",
                            end="B",
                            weight=5.0,
                            customer_id=1,
                            route_id=99,
                        ),
                    ),
                ),
                "references missing route 99",
            ),
            (
                "missing package",
                self.make_snapshot(
                    routes=(
                        RouteSnapshot(
                            route_id=1,
                            locations=("A", "B"),
                            departure_time=None,
                            truck_vehicle_id=None,
                            package_ids=(99,),
                        ),
                    )
                ),
                "references missing package 99",
            ),
            (
                "missing truck",
                self.make_snapshot(
                    routes=(
                        RouteSnapshot(
                            route_id=1,
                            locations=("A", "B"),
                            departure_time=None,
                            truck_vehicle_id=9999,
                            package_ids=(),
                        ),
                    )
                ),
                "references missing truck 9999",
            ),
        )

        for label, snapshot, message in missing_reference_cases:
            with self.subTest(label=label):
                with self.assertRaises(WorldStateCorruptionError) as ctx:
                    self.service.apply_snapshot(snapshot)

                self.assertIn(message, str(ctx.exception))

    def test_apply_snapshot_rejects_package_route_forward_inconsistency(self) -> None:
        snapshot = self.make_snapshot(
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="A",
                    end="B",
                    weight=5.0,
                    customer_id=1,
                    route_id=1,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
                    package_ids=(),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("does not include that package", str(ctx.exception))

    def test_apply_snapshot_restores_customer_package_backrefs(self) -> None:
        snapshot = self.make_snapshot(
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="A",
                    end="B",
                    weight=5.0,
                    customer_id=1,
                    route_id=1,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
                    package_ids=(1,),
                ),
            ),
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
        self.assertEqual(route.packages, [package])

    def test_apply_snapshot_restores_truck_assignment_state(self) -> None:
        departure_time = datetime(2099, 1, 1, 10, 0, 0)
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                    package_ids=(),
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
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=dt_to_str(datetime(2025, 1, 1, 10, 0, 0)),
                    truck_vehicle_id=1001,
                    package_ids=(),
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
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=1001,
                    package_ids=(),
                ),
                RouteSnapshot(
                    route_id=2,
                    locations=("B", "C"),
                    departure_time=None,
                    truck_vehicle_id=1001,
                    package_ids=(),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("assigned to multiple routes", str(ctx.exception))

    def test_apply_snapshot_rejects_route_package_reverse_inconsistency(self) -> None:
        snapshot = self.make_snapshot(
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="A",
                    end="B",
                    weight=5.0,
                    customer_id=1,
                    route_id=None,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
                    package_ids=(1,),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("includes package 1", str(ctx.exception))

    def test_apply_snapshot_restores_scheduled_and_unassigned_package_state(self) -> None:
        departure_time = datetime(2025, 1, 1, 10, 0, 0)
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 3, 2),
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="A",
                    end="C",
                    weight=5.0,
                    customer_id=1,
                    route_id=1,
                ),
                PackageSnapshot(
                    package_id=2,
                    start="A",
                    end="B",
                    weight=4.0,
                    customer_id=1,
                    route_id=None,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B", "C"),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=None,
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
        self.assertEqual(assigned_package.expected_arrival, route.arrival_time_at("C"))
        self.assertIsNone(unassigned_package.route)
        self.assertIsNone(unassigned_package.expected_arrival)

    def test_apply_snapshot_updates_repo_indexes_and_next_ids(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(4, 5, 6),
            customers=(
                CustomerSnapshot(
                    customer_id=3,
                    name="Alice",
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
                RouteSnapshot(
                    route_id=5,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
                    package_ids=(),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("Invalid next_route_id in snapshot", str(ctx.exception))

    def test_apply_snapshot_clears_existing_truck_bindings_when_snapshot_has_none(self) -> None:
        route = DeliveryRoute("A", "B", departure_time=datetime(2025, 1, 1, 8, 0, 0), route_id=1)
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
            start_location="A",
            end_location="B",
            weight=5.0,
            customer=customer,
        )
        customer.add_package(package)
        self.package_repo.add(package)

        route = DeliveryRoute("A", "B", departure_time=datetime(2025, 1, 1, 9, 0, 0), route_id=1)
        route.assign_package(package)
        self.route_repo.add(route)

        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.assign(route)
        route.truck = truck

        snapshot = self.make_snapshot(
            customers=(),
            packages=(
                PackageSnapshot(
                    package_id=2,
                    start="A",
                    end="B",
                    weight=4.0,
                    customer_id=99,
                    route_id=None,
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
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="C",
                    end="B",
                    weight=5.0,
                    customer_id=1,
                    route_id=1,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
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
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="A",
                    end="C",
                    weight=5.0,
                    customer_id=1,
                    route_id=1,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
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
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="B",
                    end="A",
                    weight=5.0,
                    customer_id=1,
                    route_id=1,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B", "C"),
                    departure_time=None,
                    truck_vehicle_id=None,
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
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="C",
                    end="A",
                    weight=5.0,
                    customer_id=1,
                    route_id=1,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
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
            start_location="A",
            end_location="B",
            weight=5.0,
            customer=existing_customer,
        )
        existing_customer.add_package(existing_package)
        self.package_repo.add(existing_package)

        existing_route = DeliveryRoute(
            "A",
            "B",
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
            customers=(CustomerSnapshot(customer_id=2, name="New", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=2,
                    start="C",
                    end="A",
                    weight=4.0,
                    customer_id=2,
                    route_id=2,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=2,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
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
        self.assertEqual(existing_route.packages, [existing_package])
        self.assertIs(truck.route, existing_route)
        self.assertEqual(truck.status, TruckStatus.ON_THE_WAY)

    def test_apply_snapshot_wraps_candidate_reconciliation_failure_as_corruption(self) -> None:
        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=dt_to_str(datetime(2099, 1, 1, 10, 0, 0)),
                    truck_vehicle_id=None,
                    package_ids=(),
                ),
            ),
        )

        with (
            patch.object(
                self.service,
                "_reconcile_candidate_world",
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
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=None,
                    package_ids=(),
                ),
            ),
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
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=None,
                    truck_vehicle_id=1001,
                    package_ids=(),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("has no departure time", str(ctx.exception))

    def test_apply_snapshot_rejects_truck_assignment_when_package_weight_exceeds_capacity(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.capacity = 10

        departure_time = datetime(2099, 1, 1, 10, 0, 0)

        snapshot = self.make_snapshot(
            counters=CountersSnapshot(2, 2, 2),
            customers=(CustomerSnapshot(customer_id=1, name="Alice", email="", phone=""),),
            packages=(
                PackageSnapshot(
                    package_id=1,
                    start="A",
                    end="B",
                    weight=11.0,
                    customer_id=1,
                    route_id=1,
                ),
            ),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                    package_ids=(1,),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("exceeds capacity", str(ctx.exception))

    def test_apply_snapshot_rejects_truck_assignment_when_route_exceeds_range(self) -> None:
        truck = self.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.max_range = 50

        departure_time = datetime(2099, 1, 1, 10, 0, 0)

        snapshot = self.make_snapshot(
            counters=CountersSnapshot(1, 1, 2),
            routes=(
                RouteSnapshot(
                    route_id=1,
                    locations=("A", "B"),
                    departure_time=dt_to_str(departure_time),
                    truck_vehicle_id=1001,
                    package_ids=(),
                ),
            ),
        )

        with self.assertRaises(WorldStateCorruptionError) as ctx:
            self.service.apply_snapshot(snapshot)

        self.assertIn("exceeds range", str(ctx.exception))
