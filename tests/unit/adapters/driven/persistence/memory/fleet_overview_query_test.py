"""Tests for the in-memory fleet-overview query projection."""

import unittest
from datetime import datetime, timedelta
from typing import cast
from unittest.mock import MagicMock

from src.adapters.driven.persistence.memory.fleet_overview_query import InMemoryFleetOverviewQuery
from src.application.results.fleet_overview import AtStopPosition, InTransitPosition
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.route_schedule import RoutePosition, RoutePositionKind
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.truck_repository import TruckRepositoryPort

GENERATED_AT = datetime(2030, 1, 1, 10, 0)


class _PackageStub:
    """Package attributes consumed by the overview query."""

    def __init__(
        self,
        *,
        status: ItemStatus,
        route_id: int | None,
        expected_arrival: datetime | None,
    ) -> None:
        self.status = status
        self.route_id = route_id
        self.expected_arrival = expected_arrival


class _TruckStub:
    """Truck attributes consumed by the overview query."""

    def __init__(
        self,
        *,
        vehicle_id: int,
        status: TruckStatus,
        capacity: int = 8_000,
        current_location: LocationCode | None = None,
    ) -> None:
        self.vehicle_id = vehicle_id
        self.status = status
        self.capacity = capacity
        self.current_location = current_location


class _RouteStub:
    """Route behavior and attributes consumed by the overview query."""

    def __init__(
        self,
        *,
        route_id: int,
        status: RouteStatus,
        position: RoutePosition,
        eta_final: datetime | None = None,
        packages: tuple[object, ...] = (),
        truck: _TruckStub | None = None,
        maximum_segment_load: float = 0.0,
        start_location: LocationCode = LocationCode("SYD"),
        end_location: LocationCode = LocationCode("MEL"),
    ) -> None:
        self.route_id = route_id
        self.status = status
        self.start_location = start_location
        self.end_location = end_location
        self.eta_final = eta_final
        self.packages = packages
        self.truck = truck
        self._position = position
        self._maximum_segment_load = maximum_segment_load
        self.position_calls: list[datetime] = []

    def current_position(self, now: datetime) -> RoutePosition:
        """Return the configured position and capture the query time."""
        self.position_calls.append(now)
        return self._position

    def maximum_segment_load(self) -> float:
        """Return the configured maximum simultaneous route load."""
        return self._maximum_segment_load


def _package(
    *,
    status: ItemStatus,
    route_id: int | None,
    expected_arrival: datetime | None = None,
) -> DeliveryPackage:
    """Return a package-shaped test stub."""
    return cast(
        DeliveryPackage,
        _PackageStub(status=status, route_id=route_id, expected_arrival=expected_arrival),
    )


def _truck(
    *,
    vehicle_id: int,
    status: TruckStatus,
    current_location: LocationCode | None,
    capacity: int = 8_000,
) -> Truck:
    """Return a truck-shaped test stub."""
    return cast(
        Truck,
        _TruckStub(
            vehicle_id=vehicle_id,
            status=status,
            current_location=current_location,
            capacity=capacity,
        ),
    )


def _route(
    *,
    route_id: int,
    status: RouteStatus,
    position: RoutePosition,
    eta_final: datetime | None = None,
    package_count: int = 0,
    truck: Truck | None = None,
    maximum_segment_load: float = 0.0,
) -> _RouteStub:
    """Return a route test stub with the requested operational state."""
    return _RouteStub(
        route_id=route_id,
        status=status,
        position=position,
        eta_final=eta_final,
        packages=tuple(object() for _ in range(package_count)),
        truck=cast(_TruckStub | None, truck),
        maximum_segment_load=maximum_segment_load,
    )


class InMemoryFleetOverviewQueryShould(unittest.TestCase):
    """Validate fleet metrics, active-route mapping, and ordering."""

    def setUp(self) -> None:
        """Create empty repository snapshots and the query under test."""
        self.package_repository = MagicMock(spec=PackageRepositoryPort)
        self.route_repository = MagicMock(spec=RouteRepositoryPort)
        self.truck_repository = MagicMock(spec=TruckRepositoryPort)
        self.package_repository.list_all.return_value = []
        self.route_repository.list_all.return_value = []
        self.truck_repository.list_fleet.return_value = []
        self.query = InMemoryFleetOverviewQuery(
            package_repository=self.package_repository,
            route_repository=self.route_repository,
            truck_repository=self.truck_repository,
        )

    def test_empty_repositories_produce_zero_counts_and_no_active_routes(self) -> None:
        """Represent an empty runtime world without special cases."""
        overview = self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=10)

        self.assertEqual(overview.generated_at, GENERATED_AT)
        self.assertEqual(overview.packages.by_status.total, 0)
        self.assertEqual(overview.packages.unassigned, 0)
        self.assertEqual(overview.packages.past_due, 0)
        self.assertEqual(overview.routes.by_status.total, 0)
        self.assertEqual(overview.routes.past_due, 0)
        self.assertEqual(overview.trucks.by_status.total, 0)
        self.assertEqual(overview.trucks.unknown_location, 0)
        self.assertEqual(overview.active_routes, ())

    def test_calculates_all_status_and_cross_cutting_metrics_from_single_snapshots(self) -> None:
        """Count statuses, assignments, deadlines, and unknown locations."""
        self.package_repository.list_all.return_value = [
            _package(
                status=ItemStatus.TODO,
                route_id=None,
                expected_arrival=GENERATED_AT - timedelta(seconds=1),
            ),
            _package(
                status=ItemStatus.IN_PROGRESS,
                route_id=1,
                expected_arrival=GENERATED_AT,
            ),
            _package(
                status=ItemStatus.DONE,
                route_id=1,
                expected_arrival=GENERATED_AT - timedelta(days=1),
            ),
            _package(status=ItemStatus.TODO, route_id=2),
        ]
        routes = [
            _route(
                route_id=1,
                status=RouteStatus.PLANNED,
                position=RoutePosition(RoutePositionKind.UNSCHEDULED),
            ),
            _route(
                route_id=2,
                status=RouteStatus.SCHEDULED,
                position=RoutePosition(RoutePositionKind.BEFORE_START),
                eta_final=GENERATED_AT - timedelta(seconds=1),
            ),
            _route(
                route_id=3,
                status=RouteStatus.IN_PROGRESS,
                position=RoutePosition(RoutePositionKind.AFTER_END),
                eta_final=GENERATED_AT,
            ),
            _route(
                route_id=4,
                status=RouteStatus.COMPLETED,
                position=RoutePosition(RoutePositionKind.AFTER_END),
                eta_final=GENERATED_AT - timedelta(days=1),
            ),
        ]
        self.route_repository.list_all.return_value = routes
        self.truck_repository.list_fleet.return_value = [
            _truck(vehicle_id=1001, status=TruckStatus.FREE, current_location=None),
            _truck(
                vehicle_id=1002,
                status=TruckStatus.ON_THE_WAY,
                current_location=LocationCode("SYD"),
            ),
        ]

        overview = self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=10)

        self.assertEqual(overview.packages.by_status.todo, 2)
        self.assertEqual(overview.packages.by_status.in_progress, 1)
        self.assertEqual(overview.packages.by_status.done, 1)
        self.assertEqual(overview.packages.unassigned, 1)
        self.assertEqual(overview.packages.past_due, 1)
        self.assertEqual(overview.routes.by_status.planned, 1)
        self.assertEqual(overview.routes.by_status.scheduled, 1)
        self.assertEqual(overview.routes.by_status.in_progress, 1)
        self.assertEqual(overview.routes.by_status.completed, 1)
        self.assertEqual(overview.routes.past_due, 1)
        self.assertEqual(overview.trucks.by_status.free, 1)
        self.assertEqual(overview.trucks.by_status.on_the_way, 1)
        self.assertEqual(overview.trucks.unknown_location, 1)
        self.package_repository.list_unassigned.assert_not_called()
        self.package_repository.list_all.assert_called_once_with()
        self.route_repository.list_all.assert_called_once_with()
        self.truck_repository.list_fleet.assert_called_once_with()

    def test_maps_in_transit_and_at_stop_routes_with_assignment_details(self) -> None:
        """Narrow active positions and preserve package, truck, and load data."""
        assigned_truck = _truck(
            vehicle_id=1003,
            status=TruckStatus.ON_THE_WAY,
            current_location=LocationCode("MEL"),
            capacity=8_000,
        )
        in_transit = _route(
            route_id=7,
            status=RouteStatus.SCHEDULED,
            position=RoutePosition(
                RoutePositionKind.IN_TRANSIT,
                from_city=LocationCode("MEL"),
                to_city=LocationCode("ADL"),
                next_eta=GENERATED_AT + timedelta(hours=2),
            ),
            package_count=3,
            truck=assigned_truck,
            maximum_segment_load=6_200.0,
        )
        at_stop = _route(
            route_id=8,
            status=RouteStatus.IN_PROGRESS,
            position=RoutePosition(
                RoutePositionKind.AT_STOP,
                stop_city=LocationCode("MEL"),
                next_eta=None,
            ),
        )
        self.route_repository.list_all.return_value = [at_stop, in_transit]

        overview = self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=10)

        first, second = overview.active_routes
        self.assertEqual((first.route_id, second.route_id), (7, 8))
        self.assertEqual(first.status, RouteStatus.SCHEDULED)
        self.assertIsInstance(first.position, InTransitPosition)
        self.assertEqual(first.assigned_package_count, 3)
        self.assertEqual(first.truck.truck_id if first.truck else None, 1003)
        self.assertEqual(first.maximum_segment_load, 6_200.0)
        self.assertEqual(first.capacity_utilization_percent, 77.5)
        self.assertIsInstance(second.position, AtStopPosition)
        self.assertIsNone(second.truck)
        self.assertIsNone(second.capacity_utilization_percent)
        self.assertEqual(in_transit.position_calls, [GENERATED_AT])
        self.assertEqual(at_stop.position_calls, [GENERATED_AT])

    def test_excludes_completed_and_non_active_temporal_positions(self) -> None:
        """Include only non-completed routes at a stop or in transit."""
        completed = _route(
            route_id=1,
            status=RouteStatus.COMPLETED,
            position=RoutePosition(
                RoutePositionKind.AT_STOP,
                stop_city=LocationCode("MEL"),
            ),
        )
        before_start = _route(
            route_id=2,
            status=RouteStatus.SCHEDULED,
            position=RoutePosition(RoutePositionKind.BEFORE_START),
        )
        after_end = _route(
            route_id=3,
            status=RouteStatus.IN_PROGRESS,
            position=RoutePosition(RoutePositionKind.AFTER_END),
        )
        self.route_repository.list_all.return_value = [completed, before_start, after_end]

        overview = self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=10)

        self.assertEqual(overview.active_routes, ())
        self.assertEqual(completed.position_calls, [])
        self.assertEqual(before_start.position_calls, [GENERATED_AT])
        self.assertEqual(after_end.position_calls, [GENERATED_AT])

    def test_orders_by_known_eta_then_route_id_and_limits_after_sorting(self) -> None:
        """Place unknown ETAs last and apply the limit to the sorted routes."""
        routes = [
            _route(
                route_id=4,
                status=RouteStatus.IN_PROGRESS,
                position=RoutePosition(
                    RoutePositionKind.AT_STOP,
                    stop_city=LocationCode("MEL"),
                    next_eta=None,
                ),
            ),
            _route(
                route_id=3,
                status=RouteStatus.IN_PROGRESS,
                position=RoutePosition(
                    RoutePositionKind.IN_TRANSIT,
                    from_city=LocationCode("SYD"),
                    to_city=LocationCode("MEL"),
                    next_eta=GENERATED_AT + timedelta(hours=2),
                ),
            ),
            _route(
                route_id=2,
                status=RouteStatus.IN_PROGRESS,
                position=RoutePosition(
                    RoutePositionKind.IN_TRANSIT,
                    from_city=LocationCode("SYD"),
                    to_city=LocationCode("MEL"),
                    next_eta=GENERATED_AT + timedelta(hours=1),
                ),
            ),
            _route(
                route_id=1,
                status=RouteStatus.IN_PROGRESS,
                position=RoutePosition(
                    RoutePositionKind.IN_TRANSIT,
                    from_city=LocationCode("SYD"),
                    to_city=LocationCode("MEL"),
                    next_eta=GENERATED_AT + timedelta(hours=1),
                ),
            ),
        ]
        self.route_repository.list_all.return_value = routes

        limited = self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=3)
        complete = self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=10)

        self.assertEqual(tuple(route.route_id for route in limited.active_routes), (1, 2, 3))
        self.assertEqual(tuple(route.route_id for route in complete.active_routes), (1, 2, 3, 4))

    def test_rejects_invalid_route_limits_before_reading_repositories(self) -> None:
        """Prevent negative slicing and unsupported oversized responses."""
        for limit in (0, -1, 101):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=limit)

        with self.assertRaises(TypeError):
            self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=True)

        self.package_repository.list_all.assert_not_called()
        self.route_repository.list_all.assert_not_called()
        self.truck_repository.list_fleet.assert_not_called()

    def test_accepts_maximum_supported_route_limit(self) -> None:
        """Allow the documented upper route-limit boundary."""
        overview = self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=100)

        self.assertEqual(overview.active_routes, ())

    def test_rejects_in_transit_position_missing_required_fields(self) -> None:
        """Surface malformed in-transit domain positions at the mapping boundary."""
        malformed_positions = (
            RoutePosition(
                RoutePositionKind.IN_TRANSIT,
                to_city=LocationCode("MEL"),
                next_eta=GENERATED_AT,
            ),
            RoutePosition(
                RoutePositionKind.IN_TRANSIT,
                from_city=LocationCode("SYD"),
                next_eta=GENERATED_AT,
            ),
            RoutePosition(
                RoutePositionKind.IN_TRANSIT,
                from_city=LocationCode("SYD"),
                to_city=LocationCode("MEL"),
            ),
        )

        for position in malformed_positions:
            self.route_repository.list_all.return_value = [
                _route(route_id=1, status=RouteStatus.IN_PROGRESS, position=position)
            ]
            with self.subTest(position=position), self.assertRaisesRegex(
                RuntimeError,
                "missing segment information",
            ):
                self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=10)

    def test_rejects_at_stop_position_without_stop_location(self) -> None:
        """Surface malformed at-stop domain positions at the mapping boundary."""
        self.route_repository.list_all.return_value = [
            _route(
                route_id=1,
                status=RouteStatus.IN_PROGRESS,
                position=RoutePosition(RoutePositionKind.AT_STOP),
            )
        ]

        with self.assertRaisesRegex(RuntimeError, "missing its stop location"):
            self.query.get_overview(generated_at=GENERATED_AT, active_route_limit=10)


if __name__ == "__main__":
    unittest.main()
