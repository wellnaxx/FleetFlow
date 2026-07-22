from __future__ import annotations

import unittest
from datetime import datetime
from typing import TYPE_CHECKING, cast

from src.domain.enums.package_assignment_rejection_reasons import PackageAssignmentRejectionReason
from src.domain.services.package_assignment_policy import PackageAssignmentPolicy
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.route_schedule import RoutePosition, RoutePositionKind

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.value_objects.package_assignment_decision import PackageAssignmentDecision

NOW = datetime(2025, 1, 1, 8, 0)
AAA = LocationCode("AAA")
BBB = LocationCode("BBB")
CCC = LocationCode("CCC")
DDD = LocationCode("DDD")


class _Package:
    def __init__(
        self,
        package_id: int,
        start: LocationCode,
        end: LocationCode,
        weight: float,
    ) -> None:
        self.package_id = package_id
        self.start_location = start
        self.end_location = end
        self.weight = weight


class _Truck:
    def __init__(self, *, capacity: float, max_range: int, vehicle_id: int = 10) -> None:
        self.vehicle_id = vehicle_id
        self.capacity = capacity
        self.max_range = max_range


class _Route:
    def __init__(self) -> None:
        self.route_id = 7
        self.locations = [AAA, BBB, CCC, DDD]
        self.packages: tuple[_Package, ...] = ()
        self.truck: _Truck | None = None
        self.departure_time: datetime | None = None
        self.total_distance_km = 600
        self.position = RoutePosition(kind=RoutePositionKind.UNSCHEDULED, stop_city=AAA)

    def includes_in_order(self, start: LocationCode, end: LocationCode) -> bool:
        indices = {location: index for index, location in enumerate(self.locations)}
        return start in indices and end in indices and indices[start] < indices[end]

    def current_position(self, _: datetime | None) -> RoutePosition:
        return self.position


def evaluate(
    route: _Route,
    package: _Package,
    *,
    now: datetime | None = NOW,
) -> PackageAssignmentDecision:
    return PackageAssignmentPolicy.evaluate(
        route=cast("DeliveryRoute", route),
        package=cast("DeliveryPackage", package),
        now=now,
    )


class PackageAssignmentPolicy_Should(unittest.TestCase):
    def test_accepts_compatible_package_when_route_has_no_truck(self) -> None:
        decision = evaluate(_Route(), _Package(1, AAA, DDD, 10))

        self.assertTrue(decision.accepted)

    def test_rejects_package_when_route_does_not_contain_both_locations(self) -> None:
        decision = evaluate(_Route(), _Package(1, AAA, LocationCode("ZZZ"), 10))

        self.assertEqual(decision.reason, PackageAssignmentRejectionReason.LOCATIONS_NOT_ON_ROUTE)
        self.assertIn("does not include start/end", decision.message or "")

    def test_rejects_package_when_route_visits_locations_out_of_order(self) -> None:
        decision = evaluate(_Route(), _Package(1, CCC, BBB, 10))

        self.assertEqual(decision.reason, PackageAssignmentRejectionReason.LOCATIONS_OUT_OF_ORDER)
        self.assertIn("does not pass from CCC to BBB in order", decision.message or "")

    def test_uses_current_position_when_time_is_omitted(self) -> None:
        package = _Package(1, BBB, DDD, 10)

        route_without_time = _Route()
        route_without_time.departure_time = NOW
        route_without_time.position = RoutePosition(kind=RoutePositionKind.AFTER_END, stop_city=DDD)

        decision = evaluate(route_without_time, package, now=None)

        self.assertEqual(decision.reason, PackageAssignmentRejectionReason.PICKUP_ALREADY_PASSED)

    def test_skips_pickup_progress_for_unscheduled_route(self) -> None:
        package = _Package(1, BBB, DDD, 10)

        unscheduled_route = _Route()
        unscheduled_route.position = RoutePosition(kind=RoutePositionKind.AFTER_END, stop_city=DDD)

        self.assertTrue(evaluate(unscheduled_route, package).accepted)

    def test_evaluates_pickup_progress_at_route_boundaries(self) -> None:
        package = _Package(1, BBB, DDD, 10)
        test_cases = [
            (RoutePosition(kind=RoutePositionKind.BEFORE_START, stop_city=AAA), True),
            (RoutePosition(kind=RoutePositionKind.AT_STOP, stop_city=BBB), True),
            (RoutePosition(kind=RoutePositionKind.AT_STOP, stop_city=CCC), False),
            (
                RoutePosition(kind=RoutePositionKind.IN_TRANSIT, from_city=AAA, to_city=BBB),
                True,
            ),
            (
                RoutePosition(kind=RoutePositionKind.IN_TRANSIT, from_city=BBB, to_city=CCC),
                False,
            ),
            (RoutePosition(kind=RoutePositionKind.AFTER_END, stop_city=DDD), False),
        ]

        for position, accepted in test_cases:
            with self.subTest(position=position.kind, accepted=accepted):
                route = _Route()
                route.departure_time = NOW
                route.position = position

                decision = evaluate(route, package)

                self.assertEqual(decision.accepted, accepted)
                if not accepted:
                    self.assertEqual(
                        decision.reason,
                        PackageAssignmentRejectionReason.PICKUP_ALREADY_PASSED,
                    )
                    self.assertIn("already passed pickup location BBB", decision.message or "")

    def test_rejects_candidate_that_exceeds_truck_capacity(self) -> None:
        route = _Route()
        route.truck = _Truck(capacity=50, max_range=1000)
        route.packages = (_Package(1, AAA, CCC, 30),)

        decision = evaluate(route, _Package(2, BBB, DDD, 30), now=None)

        self.assertEqual(decision.reason, PackageAssignmentRejectionReason.TRUCK_CAPACITY_EXCEEDED)
        self.assertIn("segment load 60", decision.message or "")

    def test_rejects_truck_with_insufficient_route_range(self) -> None:
        route = _Route()
        route.truck = _Truck(capacity=100, max_range=500)

        decision = evaluate(route, _Package(1, AAA, DDD, 10), now=None)

        self.assertEqual(decision.reason, PackageAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT)
        self.assertIn("lacks range for 600 km", decision.message or "")

    def test_accepts_candidate_within_truck_capacity_and_range(self) -> None:
        route = _Route()
        route.truck = _Truck(capacity=100, max_range=600)

        decision = evaluate(route, _Package(1, AAA, DDD, 100), now=None)

        self.assertTrue(decision.accepted)

    def test_returns_first_rejection_before_evaluating_truck_constraints(self) -> None:
        route = _Route()
        route.truck = _Truck(capacity=1, max_range=1)

        decision = evaluate(route, _Package(1, CCC, BBB, 100), now=None)

        self.assertEqual(decision.reason, PackageAssignmentRejectionReason.LOCATIONS_OUT_OF_ORDER)
