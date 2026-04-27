import unittest
from collections.abc import Sequence
from datetime import datetime
from unittest.mock import patch

from src.adapters.driven.persistence.json.serialization import dt_to_str
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.world_state_gateway import (
    InMemoryWorldStateGateway,
    InMemoryWorldStateRuntime,
)
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
from src.application.exceptions.world_state_errors import WorldStateRuntimeSwapError
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_service import WorldStateSnapshotService
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.vehicle_manager import VehicleManager
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode


class _FailingVehicleManager(VehicleManager):
    def __init__(self) -> None:
        super().__init__()
        self.replace_attempted = False

    def replace_truck_bindings(self, bindings: Sequence[TruckBinding]) -> None:
        self.replace_attempted = True
        raise RuntimeError("truck binding failure")


def _distance(_start: str, _end: str) -> int:
    return 100


class InMemoryWorldStateGatewayTests(unittest.TestCase):
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
            "src.domain.services.vehicle_manager.Map.get_locations",
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

    def test_apply_snapshot_and_build_snapshot_round_trip(self) -> None:
        customer_repo = InMemoryCustomerRepository()
        package_repo = InMemoryPackageRepository()
        route_repo = InMemoryRouteRepository()
        vehicle_manager = VehicleManager()
        runtime_state = InMemoryWorldStateRuntime(
            customer_repo=customer_repo,
            package_repo=package_repo,
            route_repo=route_repo,
            vehicle_manager=vehicle_manager,
        )
        snapshot_service = WorldStateSnapshotService(
            customer_repo=customer_repo,
            package_repo=package_repo,
            route_repo=route_repo,
            vehicle_manager=vehicle_manager,
            runtime_state=runtime_state,
            reconciler=WorldStateReconciliationService(),
        )
        gateway = InMemoryWorldStateGateway(snapshot_service=snapshot_service)

        snapshot = WorldStateSnapshot(
            schema_version=2,
            world=WorldSnapshotData(
                counters=CountersSnapshot(2, 2, 2),
                customers=(
                    CustomerSnapshot(
                        customer_id=1,
                        name="Alice",
                        email="alice@example.com",
                        phone="0412345678",
                    ),
                ),
                packages=(
                    PackageSnapshot(
                        package_id=1,
                        start=LocationCode("A"),
                        end=LocationCode("B"),
                        weight=5.0,
                        customer_id=1,
                        route_id=1,
                    ),
                ),
                routes=(
                    RouteSnapshot(
                        route_id=1,
                        locations=(LocationCode("A"), LocationCode("B")),
                        departure_time=dt_to_str(datetime(2099, 1, 1, 10, 0, 0)),
                        truck_vehicle_id=1001,
                        package_ids=(1,),
                    ),
                ),
                trucks=(),
            ),
        )

        gateway.apply_snapshot(snapshot)
        rebuilt_snapshot = gateway.build_snapshot()

        self.assertEqual(rebuilt_snapshot.schema_version, 2)
        self.assertEqual(rebuilt_snapshot.world.counters, snapshot.world.counters)
        self.assertEqual(rebuilt_snapshot.world.customers, snapshot.world.customers)
        self.assertEqual(rebuilt_snapshot.world.packages, snapshot.world.packages)
        self.assertEqual(rebuilt_snapshot.world.routes, snapshot.world.routes)
        self.assertEqual(len(rebuilt_snapshot.world.trucks), len(vehicle_manager.list_fleet()))

        truck_snapshot = next(truck for truck in rebuilt_snapshot.world.trucks if truck.vehicle_id == 1001)
        route = route_repo.get_by_id(1)
        assert route is not None

        self.assertEqual(
            truck_snapshot,
            TruckSnapshot(
                vehicle_id=1001,
                status=TruckStatus.ON_THE_WAY,
                current_location=LocationCode("A"),
                route_id=1,
                busy_from=dt_to_str(datetime(2099, 1, 1, 10, 0, 0)),
                busy_until=dt_to_str(route.eta_final),
                in_transit_to=None,
            ),
        )

    def test_runtime_replacement_rolls_back_when_truck_binding_fails(self) -> None:
        customer_repo = InMemoryCustomerRepository()
        package_repo = InMemoryPackageRepository()
        route_repo = InMemoryRouteRepository()
        vehicle_manager = _FailingVehicleManager()

        runtime_state = InMemoryWorldStateRuntime(
            customer_repo=customer_repo,
            package_repo=package_repo,
            route_repo=route_repo,
            vehicle_manager=vehicle_manager,
        )

        existing_customer = Customer(
            customer_id=1,
            contact=ContactInfo(
                name="Alice",
                email="alice@example.com",
                phone_number="0412345678",
            ),
        )
        customer_repo.add(existing_customer)

        existing_package = DeliveryPackage(
            package_id=1,
            start_location=LocationCode("A"),
            end_location=LocationCode("B"),
            weight=5.0,
            customer=existing_customer,
        )
        existing_customer.add_package(existing_package)
        package_repo.add(existing_package)

        existing_route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            departure_time=datetime(2099, 1, 1, 10, 0, 0),
            route_id=1,
        )
        existing_route.assign_package(existing_package)
        route_repo.add(existing_route)

        truck = vehicle_manager.find_by_id(1001)
        assert truck is not None

        truck.assign(existing_route)
        truck.current_location = LocationCode("A")
        truck.in_transit_to = LocationCode("B")
        existing_route.truck = truck

        previous_status = truck.status
        previous_location = truck.current_location
        previous_route = truck.route
        previous_busy_from = truck.busy_from
        previous_busy_until = truck.busy_until
        previous_in_transit_to = truck.in_transit_to

        with self.assertRaises(WorldStateRuntimeSwapError) as ctx:
            runtime_state.replace_world_state(
                customers_by_id={},
                packages_by_id={},
                routes_by_id={},
                counters=CountersSnapshot(1, 1, 1),
                truck_bindings=[],
            )

        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)

        self.assertTrue(vehicle_manager.replace_attempted)

        self.assertIs(customer_repo.get_by_id(1), existing_customer)
        self.assertIs(package_repo.get_by_id(1), existing_package)
        self.assertIs(route_repo.get_by_id(1), existing_route)

        self.assertEqual(customer_repo.peek_next_id(), 2)
        self.assertEqual(package_repo.peek_next_id(), 2)
        self.assertEqual(route_repo.peek_next_id(), 2)

        self.assertEqual(truck.status, previous_status)
        self.assertEqual(truck.current_location, previous_location)
        self.assertIs(truck.route, previous_route)
        self.assertEqual(truck.busy_from, previous_busy_from)
        self.assertEqual(truck.busy_until, previous_busy_until)
        self.assertEqual(truck.in_transit_to, previous_in_transit_to)

        self.assertIs(existing_route.truck, truck)
        self.assertIs(existing_package.route, existing_route)
