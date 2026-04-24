import unittest
from unittest.mock import patch

from src.adapters.driven.persistence.json.serialization import dt_to_str
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.world_state_gateway import (
    InMemoryWorldStateGateway,
    InMemoryWorldStateRuntime,
)
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_service import WorldStateSnapshotService
from src.domain.entities.customer import Customer
from src.domain.services.vehicle_manager import VehicleManager
from src.domain.value_objects.contact_info import ContactInfo


class _FailingVehicleManager(VehicleManager):
    def __init__(self) -> None:
        super().__init__()
        self.replace_attempted = False

    def replace_truck_bindings(self, bindings):  # type: ignore[no-untyped-def]
        self.replace_attempted = True
        raise RuntimeError("truck binding failure")


def _distance(_start: str, _end: str) -> int:
    return 100


class InMemoryWorldStateGatewayTests(unittest.TestCase):
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
            schema_version=1,
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
                        departure_time=dt_to_str(None),
                        truck_vehicle_id=1001,
                        package_ids=(1,),
                    ),
                ),
            ),
        )

        gateway.apply_snapshot(snapshot)
        rebuilt_snapshot = gateway.build_snapshot()

        self.assertEqual(rebuilt_snapshot, snapshot)

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
            contact=ContactInfo(name="Alice", email="alice@example.com", phone_number="0412345678"),
        )
        customer_repo.add(existing_customer)

        with self.assertRaises(RuntimeError):
            runtime_state.replace_world_state(
                customers_by_id={},
                packages_by_id={},
                routes_by_id={},
                counters=CountersSnapshot(1, 1, 1),
                truck_bindings=[],
            )

        self.assertTrue(vehicle_manager.replace_attempted)
        self.assertIs(customer_repo.get_by_id(1), existing_customer)
        self.assertEqual(customer_repo.peek_next_id(), 2)
