import unittest
from unittest.mock import patch

from src.adapters.driven.persistence.json.serialization import dt_to_str
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.world_state_gateway import InMemoryWorldStateGateway
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.domain.services.vehicle_manager import VehicleManager


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
        gateway = InMemoryWorldStateGateway(
            customer_repo=InMemoryCustomerRepository(),
            package_repo=InMemoryPackageRepository(),
            route_repo=InMemoryRouteRepository(),
            vehicle_manager=VehicleManager(),
        )
        snapshot = WorldStateSnapshot(
            schema_version=1,
            world=WorldSnapshotData(
                counters=CountersSnapshot(2, 2, 2),
                customers=[
                    CustomerSnapshot(
                        customer_id=1,
                        name="Alice",
                        email="alice@example.com",
                        phone="0412345678",
                    )
                ],
                packages=[
                    PackageSnapshot(
                        package_id=1,
                        start="A",
                        end="B",
                        weight=5.0,
                        customer_id=1,
                        route_id=1,
                    )
                ],
                routes=[
                    RouteSnapshot(
                        route_id=1,
                        locations=["A", "B"],
                        departure_time=dt_to_str(None),
                        truck_vehicle_id=1001,
                        package_ids=[1],
                    )
                ],
            ),
        )

        gateway.apply_snapshot(snapshot)
        rebuilt_snapshot = gateway.build_snapshot()

        self.assertEqual(rebuilt_snapshot, snapshot)
