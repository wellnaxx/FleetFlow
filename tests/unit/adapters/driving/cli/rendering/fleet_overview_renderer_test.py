"""Tests for fleet-overview CLI rendering."""

import unittest
from datetime import datetime

from src.adapters.driving.cli.rendering.fleet_overview_renderer import render_fleet_overview
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

GENERATED_AT = datetime(2030, 1, 1, 12, 34, 56)
SYD = LocationCode("SYD")
MEL = LocationCode("MEL")
ADL = LocationCode("ADL")


def _overview(
    active_routes: tuple[ActiveRouteOverview, ...] = (),
) -> FleetOverview:
    """Return a fleet overview containing representative aggregate counts."""
    return FleetOverview(
        generated_at=GENERATED_AT,
        packages=PackageOverview(
            by_status=PackageStatusCounts(todo=3, in_progress=2, done=1),
            unassigned=2,
            past_due=1,
        ),
        routes=RouteOverview(
            by_status=RouteStatusCounts(
                planned=1,
                scheduled=2,
                in_progress=1,
                completed=1,
            ),
            past_due=2,
        ),
        trucks=TruckOverview(
            by_status=TruckStatusCounts(free=2, on_the_way=1),
            unknown_location=1,
        ),
        active_routes=active_routes,
    )


class FleetOverviewRendererShould(unittest.TestCase):
    """Validate aggregate, position, truck, load, and empty-state formatting."""

    def test_renders_aggregate_sections_and_empty_active_routes(self) -> None:
        """Render every aggregate count with a clear empty active-route state."""
        result = render_fleet_overview(_overview())

        self.assertEqual(
            result,
            "Fleet Overview\n"
            "Generated at: 2030-01-01 12:34:56\n"
            "\n"
            "Packages:\n"
            "  Total: 6\n"
            "  To do: 3\n"
            "  In progress: 2\n"
            "  Done: 1\n"
            "  Unassigned: 2\n"
            "  Past due: 1\n"
            "\n"
            "Routes:\n"
            "  Total: 5\n"
            "  Planned: 1\n"
            "  Scheduled: 2\n"
            "  In progress: 1\n"
            "  Completed: 1\n"
            "  Past due: 2\n"
            "\n"
            "Trucks:\n"
            "  Total: 3\n"
            "  Free: 2\n"
            "  On the way: 1\n"
            "  Unknown location: 1\n"
            "\n"
            "Active Routes (0):\n"
            "  None",
        )

    def test_renders_in_transit_route_with_truck_and_utilization(self) -> None:
        """Render segment progress, package load, and rounded truck utilization."""
        route = ActiveRouteOverview(
            route_id=21,
            status=RouteStatus.IN_PROGRESS,
            start_location=SYD,
            end_location=ADL,
            position=InTransitPosition(
                from_location=SYD,
                to_location=MEL,
                next_eta=datetime(2030, 1, 1, 14, 0),
            ),
            assigned_package_count=3,
            truck=AssignedTruckOverview(truck_id=1001, capacity=1_000),
            maximum_segment_load=333.33,
        )

        result = render_fleet_overview(_overview((route,)))

        self.assertIn("  Route 21: SYD -> ADL", result)
        self.assertIn("    Status: IN_PROGRESS", result)
        self.assertIn("    Position: SYD -> MEL; ETA: 2030-01-01 14:00", result)
        self.assertIn("    Packages: 3", result)
        self.assertIn("    Maximum segment load: 333.33 kg", result)
        self.assertIn("    Truck: 1001 (33.3% utilized)", result)

    def test_renders_at_stop_with_next_eta_and_without_truck(self) -> None:
        """Render an intermediate stop and an explicitly unassigned truck."""
        route = ActiveRouteOverview(
            route_id=22,
            status=RouteStatus.SCHEDULED,
            start_location=SYD,
            end_location=ADL,
            position=AtStopPosition(
                stop_location=MEL,
                next_eta=datetime(2030, 1, 1, 16, 30),
            ),
            assigned_package_count=0,
            truck=None,
            maximum_segment_load=0,
        )

        result = render_fleet_overview(_overview((route,)))

        self.assertIn("    Position: At MEL; next ETA: 2030-01-01 16:30", result)
        self.assertIn("    Maximum segment load: 0.00 kg", result)
        self.assertIn("    Truck: Not assigned", result)

    def test_renders_final_stop_and_preserves_adapter_route_order(self) -> None:
        """Label a final stop and retain the supplied active-route ordering."""
        final_route = ActiveRouteOverview(
            route_id=30,
            status=RouteStatus.IN_PROGRESS,
            start_location=SYD,
            end_location=MEL,
            position=AtStopPosition(stop_location=MEL, next_eta=None),
            assigned_package_count=1,
            truck=None,
            maximum_segment_load=10,
        )
        following_route = ActiveRouteOverview(
            route_id=10,
            status=RouteStatus.IN_PROGRESS,
            start_location=MEL,
            end_location=ADL,
            position=InTransitPosition(
                from_location=MEL,
                to_location=ADL,
                next_eta=datetime(2030, 1, 1, 18, 0),
            ),
            assigned_package_count=1,
            truck=None,
            maximum_segment_load=20,
        )

        result = render_fleet_overview(_overview((final_route, following_route)))

        self.assertIn("    Position: At MEL; next ETA: Final stop", result)
        self.assertLess(result.index("Route 30"), result.index("Route 10"))
