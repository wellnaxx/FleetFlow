import unittest
from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

from src.application.dto.truck_binding_dto import TruckBinding
from src.application.services.vehicle_manager import VehicleManager
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_assignment_rejection_reasons import TruckAssignmentRejectionReason
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.truck_assignment_policy import RouteSuitabilityView
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.truck_assignment_decision import TruckAssignmentDecision


class _TruckRepository:
    def __init__(self, trucks: list[Truck] | None = None) -> None:
        self.trucks = trucks or []
        self.updated: list[Truck] = []

    def add(self, truck: Truck) -> None:
        self.trucks.append(truck)

    def list_fleet(self) -> list[Truck]:
        return list(self.trucks)

    def find_by_id(self, vehicle_id: int) -> Truck | None:
        return next((truck for truck in self.trucks if truck.vehicle_id == vehicle_id), None)

    def update_state(self, truck: Truck) -> None:
        self.updated.append(truck)


def _truck(vehicle_id: int) -> Truck:
    truck = Truck(vehicle_id=vehicle_id, name="Scania", capacity=1000, max_range=1000)
    truck.current_location = "SYD"
    return truck


def _route_view() -> RouteSuitabilityView:
    return cast(
        RouteSuitabilityView,
        SimpleNamespace(
            total_distance_km=100,
            start_location=LocationCode("SYD"),
            departure_time=datetime(2030, 1, 1, 10, 0),
            maximum_segment_load=lambda: 500.0,
        ),
    )


class VehicleManager_Should(unittest.TestCase):
    def test_delegates_fleet_queries_to_repository(self) -> None:
        trucks = [_truck(2), _truck(5)]
        manager = VehicleManager(_TruckRepository(trucks))

        self.assertEqual(manager.list_fleet(), trucks)
        self.assertIs(manager.find_by_id(5), trucks[1])
        self.assertIsNone(manager.find_by_id(99))

    def test_converts_policy_decisions_to_legacy_suitability_pair(self) -> None:
        truck = _truck(1)
        route = _route_view()
        rejected = TruckAssignmentDecision.reject(
            TruckAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT,
            "range too short",
        )

        with patch(
            "src.application.services.vehicle_manager.TruckAssignmentPolicy.evaluate",
            return_value=rejected,
        ) as evaluate:
            result = VehicleManager(_TruckRepository()).is_suitable_for_route(truck, route)

        self.assertEqual(result, (False, "range too short"))
        evaluate.assert_called_once_with(truck=truck, route=route)

    def test_returns_empty_reason_for_accepted_suitability_decision(self) -> None:
        with patch(
            "src.application.services.vehicle_manager.TruckAssignmentPolicy.evaluate",
            return_value=TruckAssignmentDecision.accept(),
        ):
            result = VehicleManager(_TruckRepository()).is_suitable_for_route(
                _truck(1),
                _route_view(),
            )

        self.assertEqual(result, (True, ""))

    def test_filters_and_sorts_available_trucks_using_policy(self) -> None:
        trucks = [_truck(5), _truck(2), _truck(9)]
        manager = VehicleManager(_TruckRepository(trucks))
        route = cast(DeliveryRoute, _route_view())

        def evaluate(*, truck: Truck, route: RouteSuitabilityView) -> TruckAssignmentDecision:
            del route
            if truck.vehicle_id in {2, 9}:
                return TruckAssignmentDecision.accept()
            return TruckAssignmentDecision.reject(
                TruckAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT,
                "range too short",
            )

        with patch(
            "src.application.services.vehicle_manager.TruckAssignmentPolicy.evaluate",
            side_effect=evaluate,
        ) as policy_evaluate:
            result = manager.find_available_for_route(route)

        self.assertEqual([truck.vehicle_id for truck in result], [2, 9])
        self.assertEqual(policy_evaluate.call_count, 3)

    def test_returns_empty_available_list_for_empty_fleet(self) -> None:
        manager = VehicleManager(_TruckRepository())

        self.assertEqual(manager.find_available_for_route(cast(DeliveryRoute, _route_view())), [])

    def test_replaces_truck_bindings_and_persists_each_state_transition(self) -> None:
        first = _truck(1)
        second = _truck(2)
        first.status = TruckStatus.ON_THE_WAY
        first.busy_from = datetime(2029, 1, 1, 8, 0)
        first.busy_until = datetime(2029, 1, 1, 9, 0)
        first.in_transit_to = "MEL"
        route = cast(DeliveryRoute, SimpleNamespace(truck=None))
        busy_from = datetime(2030, 1, 1, 10, 0)
        busy_until = datetime(2030, 1, 1, 14, 0)
        binding = TruckBinding(
            truck=second,
            route=route,
            status=TruckStatus.ON_THE_WAY,
            current_location=LocationCode("MEL"),
            busy_from=busy_from,
            busy_until=busy_until,
            in_transit_to=LocationCode("SYD"),
        )
        repository = _TruckRepository([first, second])

        VehicleManager(repository).replace_truck_bindings([binding])

        self.assertEqual(first.status, TruckStatus.FREE)
        self.assertIsNone(first.route)
        self.assertIsNone(first.busy_from)
        self.assertIsNone(first.busy_until)
        self.assertIsNone(first.in_transit_to)
        self.assertEqual(second.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(second.current_location, LocationCode("MEL"))
        self.assertEqual(second.busy_from, busy_from)
        self.assertEqual(second.busy_until, busy_until)
        self.assertEqual(second.in_transit_to, LocationCode("SYD"))
        self.assertIs(second.route, route)
        self.assertIs(route.truck, second)
        self.assertEqual(repository.updated, [first, second, second])

    def test_applies_unbound_truck_binding_without_route_backlink(self) -> None:
        truck = _truck(1)
        repository = _TruckRepository([truck])
        binding = TruckBinding(
            truck=truck,
            route=None,
            status=TruckStatus.FREE,
            current_location=LocationCode("MEL"),
            busy_from=None,
            busy_until=None,
            in_transit_to=None,
        )

        VehicleManager(repository).replace_truck_bindings((binding,))

        self.assertIsNone(truck.route)
        self.assertEqual(truck.current_location, LocationCode("MEL"))
        self.assertEqual(repository.updated, [truck, truck])

    def test_empty_binding_set_clears_every_fleet_truck(self) -> None:
        truck = _truck(1)
        truck.status = TruckStatus.ON_THE_WAY
        route = cast(DeliveryRoute, SimpleNamespace(truck=truck))
        truck.route = route
        repository = _TruckRepository([truck])

        VehicleManager(repository).replace_truck_bindings(())

        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertIsNone(truck.route)
        self.assertIsNone(route.truck)
        self.assertEqual(repository.updated, [truck])

    def test_rejects_inconsistent_existing_truck_route_backlinks(self) -> None:
        truck = _truck(1)
        other_truck = _truck(2)
        route = cast(DeliveryRoute, SimpleNamespace(truck=other_truck))
        truck.route = route
        repository = _TruckRepository([truck])

        with self.assertRaisesRegex(AssertionError, "backlinks must be consistent"):
            VehicleManager(repository).replace_truck_bindings(())

        self.assertIs(truck.route, route)
        self.assertIs(route.truck, other_truck)
        self.assertEqual(repository.updated, [])
