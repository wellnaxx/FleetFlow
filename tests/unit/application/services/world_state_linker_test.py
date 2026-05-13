import unittest
from datetime import datetime
from types import MappingProxyType
from unittest.mock import Mock, patch

from src.application.dto.candidate_truck_dto import CandidateTruckLink
from src.application.dto.rebuilt_world_dto import RebuiltWorld
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    RouteSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.services.world_state_linker import WorldStateLinker
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode
from src.ports.output.vehicle_manager import VehicleManagerPort


def _distance(_start: str, _end: str) -> int:
    return 100


class WorldStateLinkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.route_map_locations = patch(
            "src.domain.entities.delivery_route.Map.get_locations",
            return_value=[LocationCode("A"), LocationCode("B"), LocationCode("C")],
        )
        self.route_map_distance = patch(
            "src.domain.entities.delivery_route.Map.get_distance",
            side_effect=_distance,
        )
        self.route_map_locations.start()
        self.route_map_distance.start()
        self.addCleanup(self.route_map_locations.stop)
        self.addCleanup(self.route_map_distance.stop)

    def test_link_fallback_candidate_uses_route_assignment_state_not_live_truck_state(self) -> None:
        departure_time = datetime(2099, 1, 1, 10, 0, 0)
        real_truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)
        real_truck.status = TruckStatus.ON_THE_WAY
        real_truck.current_location = LocationCode("C")
        real_truck.busy_from = datetime(2025, 1, 1, 8, 0, 0)
        real_truck.busy_until = datetime(2025, 1, 1, 9, 0, 0)
        real_truck.in_transit_to = LocationCode("B")

        vehicle_manager = Mock(spec=VehicleManagerPort)
        vehicle_manager.list_fleet.return_value = [real_truck]
        linker = WorldStateLinker(vehicle_manager)

        route = DeliveryRoute(LocationCode("A"), LocationCode("B"), departure_time=departure_time, route_id=1)
        snapshot = WorldStateSnapshot(
            schema_version=1,
            world=WorldSnapshotData(
                counters=CountersSnapshot(1, 1, 2),
                customers=(),
                packages=(),
                routes=(
                    RouteSnapshot(
                        route_id=1,
                        locations=(LocationCode("A"), LocationCode("B")),
                        departure_time=None,
                        truck_vehicle_id=1001,
                        package_ids=(),
                    ),
                ),
            ),
        )
        rebuilt_world = RebuiltWorld(
            customers=MappingProxyType({}),
            packages=MappingProxyType({}),
            routes=MappingProxyType({1: route}),
            counters=snapshot.world.counters,
        )

        linked = linker.link(snapshot, rebuilt_world)

        candidate = linked.candidate_trucks_by_id[1001].candidate_truck
        self.assertIs(candidate.route, route)
        self.assertEqual(candidate.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(candidate.current_location, LocationCode("A"))
        self.assertEqual(candidate.busy_from, departure_time)
        self.assertEqual(candidate.busy_until, route.eta_final)
        self.assertIsNone(candidate.in_transit_to)

    def test_build_truck_bindings_preserves_existing_binding_when_route_no_longer_owns_candidate(self) -> None:
        real_truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)
        candidate_truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)
        route_from_snapshot = DeliveryRoute(LocationCode("A"), LocationCode("B"), route_id=1)
        reassigned_route = DeliveryRoute(LocationCode("B"), LocationCode("C"), route_id=2)
        candidate_truck.route = reassigned_route

        link = CandidateTruckLink(real_truck=real_truck, candidate_truck=candidate_truck)
        linker = WorldStateLinker(Mock(spec=VehicleManagerPort))

        bindings = linker.build_truck_bindings(
            route_snapshots=(
                RouteSnapshot(
                    route_id=1,
                    locations=(LocationCode("A"), LocationCode("B")),
                    departure_time=None,
                    truck_vehicle_id=1001,
                    package_ids=(),
                ),
            ),
            routes={1: route_from_snapshot, 2: reassigned_route},
            trucks_by_route_id={1: link},
            candidate_trucks_by_id={1001: link},
        )

        self.assertEqual(len(bindings), 1)
        self.assertIs(bindings[0].route, reassigned_route)


if __name__ == "__main__":
    unittest.main()
