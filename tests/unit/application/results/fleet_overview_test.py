"""Tests for fleet-overview application projections."""

import unittest
from datetime import datetime

from src.application.results.fleet_overview import (
    ActiveRouteOverview,
    AssignedTruckOverview,
    AtStopPosition,
    FleetOverview,
    InTransitPosition,
    PackageOverview,
    PackageStatusCounts,
    RouteOverview,
    RouteStatusCounts,
    TruckOverview,
    TruckStatusCounts,
)
from src.domain.enums.route_status import RouteStatus
from src.domain.value_objects.location_code import LocationCode


class FleetOverviewShould(unittest.TestCase):
    """Verify fleet-overview aggregation and route projection behavior."""

    def test_status_totals_are_derived_from_exhaustive_categories(self) -> None:
        """Calculate totals without including overlapping operational counts."""
        packages = PackageOverview(
            by_status=PackageStatusCounts(todo=3, in_progress=2, done=1),
            unassigned=2,
            past_due=1,
        )
        routes = RouteOverview(
            by_status=RouteStatusCounts(planned=1, scheduled=2, in_progress=3, completed=4),
            past_due=2,
        )
        trucks = TruckOverview(
            by_status=TruckStatusCounts(free=2, on_the_way=3),
            unknown_location=1,
        )

        self.assertEqual(packages.by_status.total, 6)
        self.assertEqual(routes.by_status.total, 10)
        self.assertEqual(trucks.by_status.total, 5)

    def test_status_counts_reject_negative_values_and_booleans(self) -> None:
        """Reject invalid aggregate values at the result-model boundary."""
        with self.assertRaises(ValueError):
            PackageStatusCounts(todo=-1, in_progress=0, done=0)
        with self.assertRaises(ValueError):
            RouteStatusCounts(planned=0, scheduled=-1, in_progress=0, completed=0)
        with self.assertRaises(ValueError):
            TruckStatusCounts(free=0, on_the_way=-1)

        with self.assertRaises(TypeError):
            PackageStatusCounts(todo=True, in_progress=0, done=0)
        with self.assertRaises(TypeError):
            RouteStatusCounts(planned=0, scheduled=True, in_progress=0, completed=0)
        with self.assertRaises(TypeError):
            TruckStatusCounts(free=0, on_the_way=True)

    def test_operational_counts_reject_negative_values(self) -> None:
        """Reject negative counts outside the exhaustive status groupings."""
        with self.assertRaises(ValueError):
            PackageOverview(PackageStatusCounts(1, 0, 0), unassigned=-1, past_due=0)
        with self.assertRaises(ValueError):
            RouteOverview(RouteStatusCounts(1, 0, 0, 0), past_due=-1)
        with self.assertRaises(ValueError):
            TruckOverview(TruckStatusCounts(1, 0), unknown_location=-1)

    def test_operational_counts_cannot_exceed_applicable_populations(self) -> None:
        """Reject internally inconsistent coherent-snapshot aggregates."""
        with self.assertRaisesRegex(ValueError, "unassigned cannot exceed"):
            PackageOverview(PackageStatusCounts(1, 0, 0), unassigned=2, past_due=0)
        with self.assertRaisesRegex(ValueError, "past_due cannot exceed the undelivered"):
            PackageOverview(PackageStatusCounts(0, 0, 1), unassigned=0, past_due=1)
        with self.assertRaisesRegex(ValueError, "past_due cannot exceed the non-completed"):
            RouteOverview(RouteStatusCounts(0, 0, 0, 1), past_due=1)
        with self.assertRaisesRegex(ValueError, "unknown_location cannot exceed"):
            TruckOverview(TruckStatusCounts(1, 0), unknown_location=2)

    def test_active_route_calculates_unrounded_segment_capacity_utilization(self) -> None:
        """Use maximum segment load rather than total assigned package weight."""
        route = ActiveRouteOverview(
            route_id=7,
            status=RouteStatus.IN_PROGRESS,
            start_location=LocationCode("SYD"),
            end_location=LocationCode("ADL"),
            position=InTransitPosition(
                from_location=LocationCode("MEL"),
                to_location=LocationCode("ADL"),
                next_eta=datetime(2030, 1, 1, 12, 0),
            ),
            assigned_package_count=8,
            truck=AssignedTruckOverview(truck_id=1003, capacity=8_000),
            maximum_segment_load=6_200.0,
        )

        self.assertEqual(route.capacity_utilization_percent, 77.5)
        self.assertEqual(route.position.kind, "in_transit")

    def test_assigned_truck_rejects_non_positive_capacity(self) -> None:
        """Prevent utilization calculations from dividing by invalid capacity."""
        for capacity in (0, -1):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                AssignedTruckOverview(truck_id=1003, capacity=capacity)

        with self.assertRaises(TypeError):
            AssignedTruckOverview(truck_id=1003, capacity=True)

    def test_active_route_without_truck_has_no_capacity_utilization(self) -> None:
        """Represent an active route without inventing truck capacity data."""
        route = ActiveRouteOverview(
            route_id=8,
            status=RouteStatus.SCHEDULED,
            start_location=LocationCode("SYD"),
            end_location=LocationCode("MEL"),
            position=AtStopPosition(
                stop_location=LocationCode("MEL"),
                next_eta=None,
            ),
            assigned_package_count=0,
            truck=None,
            maximum_segment_load=0.0,
        )

        self.assertIsNone(route.capacity_utilization_percent)
        self.assertEqual(route.position.kind, "at_stop")

    def test_active_route_rejects_invalid_assigned_package_count(self) -> None:
        """Reject negative and boolean package counts on active routes."""
        def build_route(assigned_package_count: int) -> ActiveRouteOverview:
            return ActiveRouteOverview(
                route_id=8,
                status=RouteStatus.IN_PROGRESS,
                start_location=LocationCode("SYD"),
                end_location=LocationCode("MEL"),
                position=AtStopPosition(LocationCode("SYD"), None),
                assigned_package_count=assigned_package_count,
                truck=None,
                maximum_segment_load=0.0,
            )

        with self.assertRaises(ValueError):
            build_route(-1)
        with self.assertRaises(TypeError):
            build_route(True)

    def test_active_route_rejects_invalid_maximum_segment_load(self) -> None:
        """Reject negative, non-finite, and non-numeric route load aggregates."""
        def build_route(maximum_segment_load: float) -> ActiveRouteOverview:
            return ActiveRouteOverview(
                route_id=8,
                status=RouteStatus.IN_PROGRESS,
                start_location=LocationCode("SYD"),
                end_location=LocationCode("MEL"),
                position=AtStopPosition(LocationCode("SYD"), None),
                assigned_package_count=0,
                truck=AssignedTruckOverview(truck_id=1003, capacity=8_000),
                maximum_segment_load=maximum_segment_load,
            )

        for load in (-1.0, float("nan"), float("inf"), float("-inf")):
            with self.subTest(load=load), self.assertRaises(ValueError):
                build_route(load)

        with self.assertRaises(TypeError):
            build_route(True)

    def test_fleet_overview_preserves_generation_time_and_active_route_order(self) -> None:
        """Store the coherent query timestamp and adapter-defined route order."""
        generated_at = datetime(2030, 1, 1, 10, 0)
        first_route = ActiveRouteOverview(
            route_id=1,
            status=RouteStatus.IN_PROGRESS,
            start_location=LocationCode("SYD"),
            end_location=LocationCode("MEL"),
            position=AtStopPosition(LocationCode("SYD"), generated_at),
            assigned_package_count=0,
            truck=None,
            maximum_segment_load=0.0,
        )
        second_route = ActiveRouteOverview(
            route_id=2,
            status=RouteStatus.IN_PROGRESS,
            start_location=LocationCode("MEL"),
            end_location=LocationCode("ADL"),
            position=AtStopPosition(LocationCode("MEL"), generated_at),
            assigned_package_count=0,
            truck=None,
            maximum_segment_load=0.0,
        )
        overview = FleetOverview(
            generated_at=generated_at,
            packages=PackageOverview(PackageStatusCounts(0, 0, 0), 0, 0),
            routes=RouteOverview(RouteStatusCounts(0, 0, 2, 0), 0),
            trucks=TruckOverview(TruckStatusCounts(0, 0), 0),
            active_routes=(first_route, second_route),
        )

        self.assertIs(overview.generated_at, generated_at)
        self.assertEqual(tuple(route.route_id for route in overview.active_routes), (1, 2))


if __name__ == "__main__":
    unittest.main()
