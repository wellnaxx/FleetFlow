import unittest
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import cast

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_assignment_rejection_reasons import TruckAssignmentRejectionReason
from src.domain.services.truck_assignment_policy import TruckAssignmentPolicy
from src.domain.value_objects.location_code import LocationCode


@dataclass
class _RouteView:
    total_distance_km: int = 100
    start_location: LocationCode = field(default_factory=lambda: LocationCode("SYD"))
    departure_time: datetime | None = datetime(2030, 1, 1, 10, 0)
    segment_load: float = 500

    def maximum_segment_load(self) -> float:
        return self.segment_load


def _truck(*, capacity: int = 500, max_range: int = 100) -> Truck:
    truck = Truck(vehicle_id=1, name="Scania", capacity=capacity, max_range=max_range)
    truck.current_location = "SYD"
    return truck


def _assign_current_route(
    truck: Truck,
    eta_final: datetime | None,
    *,
    end_location: str = "SYD",
) -> None:
    truck.route = cast(
        DeliveryRoute,
        SimpleNamespace(
            eta_final=eta_final,
            end_location=LocationCode(end_location),
        ),
    )


class TruckAssignmentPolicy_Should(unittest.TestCase):
    def test_accepts_free_truck_matching_route_requirements(self) -> None:
        decision = TruckAssignmentPolicy.evaluate(truck=_truck(), route=_RouteView())

        self.assertTrue(decision.accepted)
        self.assertIsNone(decision.reason)

    def test_accepts_free_truck_for_unscheduled_target_route(self) -> None:
        decision = TruckAssignmentPolicy.evaluate(
            truck=_truck(),
            route=_RouteView(departure_time=None),
        )

        self.assertTrue(decision.accepted)

    def test_rejects_truck_with_insufficient_range(self) -> None:
        decision = TruckAssignmentPolicy.evaluate(
            truck=_truck(max_range=99),
            route=_RouteView(total_distance_km=100),
        )

        self.assertEqual(decision.reason, TruckAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT)

    def test_rejects_truck_with_insufficient_segment_capacity(self) -> None:
        decision = TruckAssignmentPolicy.evaluate(
            truck=_truck(capacity=499),
            route=_RouteView(segment_load=500),
        )

        self.assertEqual(decision.reason, TruckAssignmentRejectionReason.TRUCK_CAPACITY_INSUFFICIENT)

    def test_rejects_truck_at_wrong_location(self) -> None:
        truck = _truck()
        truck.current_location = "MEL"

        decision = TruckAssignmentPolicy.evaluate(truck=truck, route=_RouteView())

        self.assertEqual(decision.reason, TruckAssignmentRejectionReason.TRUCK_AT_WRONG_LOCATION)
        self.assertIn("MEL", decision.message or "")
        self.assertIn("SYD", decision.message or "")

    def test_rejects_assigned_truck_when_target_route_is_unscheduled(self) -> None:
        truck = _truck()
        _assign_current_route(truck, datetime(2030, 1, 1, 9, 0))

        decision = TruckAssignmentPolicy.evaluate(
            truck=truck,
            route=_RouteView(departure_time=None),
        )

        self.assertEqual(decision.reason, TruckAssignmentRejectionReason.TARGET_ROUTE_UNSCHEDULED)

    def test_rejects_assigned_truck_with_unknown_current_route_eta(self) -> None:
        truck = _truck()
        _assign_current_route(truck, None)

        decision = TruckAssignmentPolicy.evaluate(truck=truck, route=_RouteView())

        self.assertEqual(
            decision.reason,
            TruckAssignmentRejectionReason.CURRENT_ROUTE_AVAILABILITY_UNKNOWN,
        )

    def test_rejects_assigned_truck_when_availability_windows_touch(self) -> None:
        departure_time = datetime(2030, 1, 1, 10, 0)
        truck = _truck()
        _assign_current_route(truck, departure_time)

        decision = TruckAssignmentPolicy.evaluate(
            truck=truck,
            route=_RouteView(departure_time=departure_time),
        )

        self.assertEqual(decision.reason, TruckAssignmentRejectionReason.AVAILABILITY_WINDOW_OVERLAP)

    def test_accepts_assigned_truck_available_before_target_departure(self) -> None:
        departure_time = datetime(2030, 1, 1, 10, 0)
        truck = _truck()
        truck.current_location = "MEL"
        _assign_current_route(truck, departure_time - timedelta(microseconds=1))

        decision = TruckAssignmentPolicy.evaluate(
            truck=truck,
            route=_RouteView(departure_time=departure_time),
        )

        self.assertTrue(decision.accepted)

    def test_rejects_assigned_truck_finishing_away_from_target_route_origin(self) -> None:
        departure_time = datetime(2030, 1, 1, 10, 0)
        truck = _truck()
        _assign_current_route(
            truck,
            departure_time - timedelta(hours=1),
            end_location="MEL",
        )

        decision = TruckAssignmentPolicy.evaluate(
            truck=truck,
            route=_RouteView(departure_time=departure_time),
        )

        self.assertEqual(decision.reason, TruckAssignmentRejectionReason.TRUCK_AT_WRONG_LOCATION)
        self.assertIn("MEL", decision.message or "")
        self.assertIn("SYD", decision.message or "")

    def test_accepts_range_and_capacity_equal_to_route_requirements(self) -> None:
        decision = TruckAssignmentPolicy.evaluate(
            truck=_truck(capacity=500, max_range=100),
            route=_RouteView(total_distance_km=100, segment_load=500),
        )

        self.assertTrue(decision.accepted)

    def test_reports_range_before_other_rejections(self) -> None:
        truck = _truck(capacity=1, max_range=1)
        truck.current_location = "MEL"

        decision = TruckAssignmentPolicy.evaluate(
            truck=truck,
            route=_RouteView(total_distance_km=100, segment_load=500),
        )

        self.assertEqual(decision.reason, TruckAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT)
