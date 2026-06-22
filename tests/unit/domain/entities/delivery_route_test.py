import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.events.route_events import (
    PackageAssignedToRoute,
    PackageDetachedFromRoute,
    RouteCompleted,
    RouteCreated,
    RouteRemoved,
    RouteScheduled,
    RouteStarted,
    TruckAssignedToRoute,
    TruckReleasedFromRoute,
)
from src.domain.exceptions import DomainConflictError, DomainValidationError, EntityNotFoundError
from src.domain.value_objects.location_code import LocationCode

LOCATIONS = [
    LocationCode("AAA"),
    LocationCode("BBB"),
    LocationCode("CCC"),
    LocationCode("DDD"),
]

DIST = {
    ("AAA", "BBB"): 100,
    ("BBB", "CCC"): 200,
    ("CCC", "DDD"): 300,
}

EVENT_TIME = datetime(2025, 1, 1, 7, 0)


def get_dist(a: str, b: str) -> int:
    return DIST[(str(LocationCode(a)), str(LocationCode(b)))]


class _Pkg:
    def __init__(
        self,
        package_id: int,
        start: str | LocationCode,
        end: str | LocationCode,
        weight: float = 0.0,
    ) -> None:
        self.package_id = package_id
        self.start_location = LocationCode(start)
        self.end_location = LocationCode(end)
        self.weight = weight
        self.route: DeliveryRoute | None = None
        self.expected_arrival: datetime | None = None
        self.status: ItemStatus = ItemStatus.TODO
        self.current_location = self.start_location

    def reset_assignment_state(self) -> None:
        self.route = None
        self.expected_arrival = None
        self.status = ItemStatus.TODO
        self.current_location = self.start_location


class _Truck:
    def __init__(
        self,
        vehicle_id: int = 1,
        capacity: int = 999999,
        max_range: int = 999999,
        current_location: str | LocationCode | None = None,
        route: DeliveryRoute | None = None,
    ) -> None:
        self.vehicle_id = vehicle_id
        self.capacity = capacity
        self.max_range = max_range
        self.current_location = LocationCode(current_location) if current_location is not None else None
        self.route = route
        self.released_force: bool | None = None

    def release(self, *, now: datetime | None = None, force: bool = False) -> bool:
        self.released_force = force
        released = self.route is not None
        self.route = None
        return released


@patch("src.domain.entities.delivery_route.Map.get_locations", return_value=LOCATIONS)
@patch("src.domain.entities.delivery_route.Map.get_distance", side_effect=get_dist)
class DeliveryRoute_Should(unittest.TestCase):
    def assert_error_contains(self, expected: str, error: str | None) -> None:
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn(expected, error)

    def test_init_validates_locations_and_sets_id_or_uses_provided(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=123)

        self.assertEqual(route.route_id, 123)
        self.assertEqual(route.start_location, LocationCode("AAA"))
        self.assertEqual(route.end_location, LocationCode("BBB"))
        self.assertEqual(route.status, RouteStatus.PLANNED)

        scheduled = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            departure_time=datetime(2025, 1, 1, 8, 0),
            route_id=124,
        )
        self.assertEqual(scheduled.status, RouteStatus.SCHEDULED)

        with self.assertRaises(DomainValidationError):
            DeliveryRoute(LocationCode("AAA"), route_id=1)

        with self.assertRaises(DomainValidationError):
            DeliveryRoute(LocationCode("AAA"), LocationCode("ZZZ"), route_id=1)

    def test_init_rejects_duplicate_locations(self, *_: object) -> None:
        with self.assertRaises(DomainValidationError) as ctx:
            DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("AAA"), route_id=1)

        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_create_records_route_created_event(self, *_: object) -> None:
        departure_time = datetime(2025, 1, 2, 8, 0)

        route = DeliveryRoute.create(
            LocationCode("AAA"),
            LocationCode("BBB"),
            departure_time=departure_time,
            route_id=7,
            occurred_at=EVENT_TIME,
        )

        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, RouteCreated)
        assert isinstance(event, RouteCreated)
        self.assertEqual(event.route_id, 7)
        self.assertEqual(event.locations, (LocationCode("AAA"), LocationCode("BBB")))
        self.assertEqual(event.departure_time, departure_time)
        self.assertEqual(event.occurred_at, EVENT_TIME)

    def test_schedule_builds_segments_and_stop_times_eta_final(self, *_: object) -> None:
        base = datetime(2025, 1, 1, 8, 0, 0)
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)

        route.schedule(base, occurred_at=EVENT_TIME)

        dur_ab = timedelta(hours=100 / DeliveryRoute.SPEED_KMPH)
        dur_bc = timedelta(hours=200 / DeliveryRoute.SPEED_KMPH)

        self.assertEqual(route.arrival_time_at(LocationCode("AAA")), base)
        self.assertEqual(route.arrival_time_at(LocationCode("BBB")), base + dur_ab)
        self.assertEqual(route.arrival_time_at(LocationCode("CCC")), base + dur_ab + dur_bc)
        self.assertEqual(route.eta_final, base + dur_ab + dur_bc)
        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, RouteScheduled)
        assert isinstance(event, RouteScheduled)
        self.assertEqual(event.route_id, 1)
        self.assertEqual(event.departure_time, base)
        self.assertEqual(event.expected_completion_time, route.eta_final)
        self.assertEqual(event.occurred_at, EVENT_TIME)

    def test_mark_started_updates_status_and_records_event(self, *_: object) -> None:
        departure_time = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            departure_time=departure_time,
            route_id=1,
        )

        route.mark_started(occurred_at=departure_time)

        self.assertEqual(route.status, RouteStatus.IN_PROGRESS)
        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, RouteStarted)
        assert isinstance(event, RouteStarted)
        self.assertEqual(event.route_id, 1)
        self.assertEqual(event.occurred_at, departure_time)

    def test_mark_started_rejects_invalid_transition_without_event(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=1)

        with self.assertRaises(DomainConflictError):
            route.mark_started(occurred_at=EVENT_TIME)

        self.assertEqual(route.status, RouteStatus.PLANNED)
        self.assertEqual(route.pending_events, ())

    def test_mark_completed_updates_status_and_records_event(self, *_: object) -> None:
        departure_time = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            departure_time=departure_time,
            route_id=1,
        )
        completion_time = route.eta_final
        assert completion_time is not None

        route.mark_completed(occurred_at=completion_time)

        self.assertEqual(route.status, RouteStatus.COMPLETED)
        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, RouteCompleted)
        assert isinstance(event, RouteCompleted)
        self.assertEqual(event.route_id, 1)
        self.assertEqual(event.occurred_at, completion_time)

    def test_mark_completed_rejects_duplicate_transition_without_new_event(self, *_: object) -> None:
        departure_time = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            departure_time=departure_time,
            route_id=1,
        )
        completion_time = route.eta_final
        assert completion_time is not None
        route.mark_completed(occurred_at=completion_time)
        checkpoint = route.event_checkpoint()

        with self.assertRaises(DomainConflictError):
            route.mark_completed(occurred_at=completion_time)

        self.assertEqual(route.status, RouteStatus.COMPLETED)
        self.assertEqual(route.event_checkpoint(), checkpoint)

    def test_total_distance_km_uses_map_sum_and_cached_segments(self, *_: object) -> None:
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            LocationCode("CCC"),
            LocationCode("DDD"),
            route_id=1,
        )

        self.assertEqual(route.total_distance_km, 100 + 200 + 300)

        route.schedule(datetime(2025, 1, 1, 9, 0), occurred_at=EVENT_TIME)
        self.assertEqual(route.total_distance_km, 100 + 200 + 300)

    def test_arrival_time_at_validations(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)

        with self.assertRaises(DomainConflictError):
            route.arrival_time_at(LocationCode("AAA"))

        route.schedule(datetime(2025, 1, 1, 9, 0), occurred_at=EVENT_TIME)

        with self.assertRaises(DomainValidationError):
            route.arrival_time_at(LocationCode("DDD"))

    def test_current_position_all_cases(self, *_: object) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        route.schedule(base, occurred_at=EVENT_TIME)

        self.assertEqual(route.status, RouteStatus.SCHEDULED)

        unscheduled_route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=2)
        unscheduled_position = unscheduled_route.current_position(base)
        self.assertEqual(unscheduled_position.kind, "UNSCHEDULED")
        self.assertEqual(unscheduled_position.stop_city, LocationCode("AAA"))

        before_start_time = base - timedelta(minutes=5)
        before_start_position = route.current_position(before_start_time)
        self.assertEqual(before_start_position.kind, "BEFORE_START")
        self.assertEqual(before_start_position.stop_city, LocationCode("AAA"))
        self.assertIsInstance(before_start_position.next_eta, datetime)

        start_time = route.arrival_time_at(LocationCode("AAA"))
        start_position = route.current_position(start_time)
        self.assertEqual(start_position.kind, "IN_TRANSIT")
        self.assertEqual(start_position.from_city, LocationCode("AAA"))
        self.assertEqual(start_position.to_city, LocationCode("BBB"))

        mid_leg_time = start_time + (route.arrival_time_at(LocationCode("BBB")) - start_time) / 2
        mid_leg_position = route.current_position(mid_leg_time)
        self.assertEqual(mid_leg_position.kind, "IN_TRANSIT")
        self.assertEqual(mid_leg_position.from_city, LocationCode("AAA"))
        self.assertEqual(mid_leg_position.to_city, LocationCode("BBB"))

        stop_b_time = route.arrival_time_at(LocationCode("BBB"))
        stop_b_position = route.current_position(stop_b_time)
        self.assertEqual(stop_b_position.kind, "AT_STOP")
        self.assertEqual(stop_b_position.stop_city, LocationCode("BBB"))

        after_end_time = route.arrival_time_at(LocationCode("CCC")) + timedelta(seconds=1)
        after_end_position = route.current_position(after_end_time)
        self.assertEqual(after_end_position.kind, "AFTER_END")
        self.assertEqual(after_end_position.stop_city, LocationCode("CCC"))

    def test_includes_in_order(self, *_: object) -> None:
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            LocationCode("CCC"),
            LocationCode("DDD"),
            route_id=1,
        )

        self.assertTrue(route.includes_in_order(LocationCode("AAA"), LocationCode("DDD")))
        self.assertTrue(route.includes_in_order(LocationCode("BBB"), LocationCode("CCC")))
        self.assertFalse(route.includes_in_order(LocationCode("CCC"), LocationCode("BBB")))
        self.assertFalse(route.includes_in_order(LocationCode("AAA"), LocationCode("AAA")))
        self.assertFalse(route.includes_in_order(LocationCode("AAA"), LocationCode("ZZZ")))

    def test_can_accept_package_checks_inclusion_capacity_and_range(self, *_: object) -> None:
        base = datetime(2025, 1, 1, 7, 0)
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            LocationCode("CCC"),
            LocationCode("DDD"),
            route_id=1,
        )
        route.schedule(base, occurred_at=EVENT_TIME)

        route.truck = _Truck(
            vehicle_id=10,
            capacity=50,
            max_range=500,
            current_location=LocationCode("AAA"),
        )  # type: ignore[reportAttributeAccessIssue]

        self.assert_error_contains(
            "does not include start/end",
            route.can_accept_package(_Pkg(1, "AAA", "ZZZ", 10)),  # type: ignore[reportArgumentType]
        )

        self.assert_error_contains(
            "does not pass from CCC to BBB in order",
            route.can_accept_package(_Pkg(2, "CCC", "BBB", 10)),  # type: ignore[reportArgumentType]
        )

        self.assert_error_contains(
            "capacity exceeded",
            route.can_accept_package(_Pkg(3, "AAA", "BBB", 60)),  # type: ignore[reportArgumentType]
        )

        assert route.truck is not None
        route.truck.capacity = 1000
        self.assert_error_contains(
            "lacks range for 600 km",
            route.can_accept_package(_Pkg(4, "AAA", "CCC", 1)),  # type: ignore[reportArgumentType]
        )

        route.truck.max_range = 1000
        self.assertIsNone(route.can_accept_package(_Pkg(5, "AAA", "CCC", 10)))  # type: ignore[reportArgumentType]

    def test_capacity_uses_maximum_segment_load_not_total_route_weight(self, *_: object) -> None:
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            LocationCode("CCC"),
            LocationCode("DDD"),
            route_id=1,
        )
        route.truck = _Truck(
            vehicle_id=10,
            capacity=50,
            max_range=1000,
            current_location=LocationCode("AAA"),
        )  # type: ignore[reportAttributeAccessIssue]

        route.assign_package(
            _Pkg(1, "AAA", "BBB", 40),  # type: ignore[reportArgumentType]
            occurred_at=EVENT_TIME,
        )
        route.assign_package(
            _Pkg(2, "BBB", "CCC", 40),  # type: ignore[reportArgumentType]
            occurred_at=EVENT_TIME,
        )

        self.assertEqual(route.total_assigned_weight(), 80)
        self.assertEqual(route.maximum_segment_load(), 40)
        self.assertIsNone(route.can_accept_package(_Pkg(3, "CCC", "DDD", 40)))  # type: ignore[reportArgumentType]

    def test_capacity_rejects_overloaded_route_segment(self, *_: object) -> None:
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            LocationCode("CCC"),
            LocationCode("DDD"),
            route_id=1,
        )
        route.truck = _Truck(
            vehicle_id=10,
            capacity=50,
            max_range=1000,
            current_location=LocationCode("AAA"),
        )  # type: ignore[reportAttributeAccessIssue]

        route.assign_package(
            _Pkg(1, "AAA", "CCC", 30),  # type: ignore[reportArgumentType]
            occurred_at=EVENT_TIME,
        )

        error = route.can_accept_package(_Pkg(2, "BBB", "DDD", 30))  # type: ignore[reportArgumentType]

        self.assert_error_contains("capacity exceeded", error)
        self.assert_error_contains("segment load 60", error)

    def test_can_accept_package_allows_before_pickup_and_blocks_after_pickup(self, *_: object) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        route.schedule(base, occurred_at=EVENT_TIME)

        start_package = _Pkg(1, "AAA", "CCC", 5)
        mid_package = _Pkg(2, "BBB", "CCC", 5)

        self.assertIsNone(
            route.can_accept_package(start_package, now=base - timedelta(seconds=1))  # type: ignore[reportArgumentType]
        )
        self.assert_error_contains(
            "already passed pickup location AAA",
            route.can_accept_package(start_package, now=base),  # type: ignore[reportArgumentType]
        )

        stop_b_time = route.arrival_time_at(LocationCode("BBB"))
        self.assertIsNone(route.can_accept_package(mid_package, now=stop_b_time))  # type: ignore[reportArgumentType]
        self.assert_error_contains(
            "already passed pickup location BBB",
            route.can_accept_package(mid_package, now=stop_b_time + timedelta(seconds=1)),  # type: ignore[reportArgumentType]
        )

    def test_can_accept_package_unscheduled_route_ignores_pickup_passed_rule(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        package = _Pkg(1, "BBB", "CCC", 5)

        self.assertIsNone(
            route.can_accept_package(package, now=datetime(2025, 1, 1, 8, 0))  # type: ignore[reportArgumentType]
        )

    def test_assign_package_sets_links_and_expected_arrival_when_scheduled(self, *_: object) -> None:
        base = datetime(2025, 1, 1, 6, 0)
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        route.schedule(base, occurred_at=EVENT_TIME)
        package = _Pkg(1, "AAA", "CCC", 5)

        route.assign_package(package, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]

        self.assertIs(package.route, route)
        self.assertIn(package, route.packages)
        self.assertIsInstance(package.expected_arrival, datetime)

        route.assign_package(package, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]
        self.assertEqual(len(route.packages), 1)

    def test_assign_package_unscheduled_sets_no_eta(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=1)
        package = _Pkg(1, "AAA", "BBB", 1)

        route.assign_package(package, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]

        self.assertIs(package.route, route)
        self.assertIsNone(package.expected_arrival)

    def test_assign_package_records_assignment_event(self, *_: object) -> None:
        departure_time = datetime(2025, 1, 1, 8, 0)
        occurred_at = datetime(2025, 1, 1, 7, 30)
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            LocationCode("CCC"),
            departure_time=departure_time,
            route_id=7,
        )
        package = _Pkg(11, "AAA", "CCC", 5)

        route.assign_package(
            package,  # type: ignore[reportArgumentType]
            now=departure_time - timedelta(minutes=1),
            occurred_at=occurred_at,
        )

        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, PackageAssignedToRoute)
        assert isinstance(event, PackageAssignedToRoute)
        self.assertEqual(event.route_id, 7)
        self.assertEqual(event.package_id, 11)
        self.assertEqual(event.expected_arrival, route.arrival_time_at(LocationCode("CCC")))
        self.assertEqual(event.occurred_at, occurred_at)

    def test_rejected_package_assignment_records_no_event(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=7)
        package = _Pkg(11, "AAA", "CCC", 5)

        with self.assertRaises(DomainConflictError):
            route.assign_package(package, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]

        self.assertEqual(route.pending_events, ())
        self.assertIsNone(package.route)

    def test_detach_package_removes_package_and_clears_assignment_state(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        package = _Pkg(1, "AAA", "CCC", 5)
        package.status = ItemStatus.IN_PROGRESS
        package.current_location = LocationCode("BBB")

        route.schedule(datetime(2025, 1, 1, 6, 0), occurred_at=EVENT_TIME)
        route.assign_package(package, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]
        route.clear_events()

        self.assertIs(package.route, route)
        self.assertIn(package, route.packages)
        self.assertIsNotNone(package.expected_arrival)

        route.detach_package(
            package,  # type: ignore[reportArgumentType]
            reason=PackageDetachmentReason.PACKAGE_REMOVED,
            occurred_at=EVENT_TIME,
        )

        self.assertIsNone(package.route)
        self.assertIsNone(package.expected_arrival)
        self.assertEqual(package.status, ItemStatus.TODO)
        self.assertEqual(package.current_location, package.start_location)
        self.assertNotIn(package, route.packages)
        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, PackageDetachedFromRoute)
        assert isinstance(event, PackageDetachedFromRoute)
        self.assertEqual(event.route_id, 1)
        self.assertEqual(event.package_id, 1)
        self.assertEqual(event.reason, PackageDetachmentReason.PACKAGE_REMOVED)
        self.assertEqual(event.occurred_at, EVENT_TIME)

    def test_detach_package_only_removes_target(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        package_1 = _Pkg(1, "AAA", "BBB", 5)
        package_2 = _Pkg(2, "AAA", "CCC", 7)

        route.assign_package(package_1, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]
        route.assign_package(package_2, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]

        route.detach_package(
            package_1,  # type: ignore[reportArgumentType]
            reason=PackageDetachmentReason.PACKAGE_REMOVED,
            occurred_at=EVENT_TIME,
        )

        self.assertIsNone(package_1.route)
        self.assertNotIn(package_1, route.packages)

        self.assertIs(package_2.route, route)
        self.assertIn(package_2, route.packages)
        self.assertEqual(len(route.packages), 1)

    def test_detach_package_raises_when_not_assigned(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        package = _Pkg(1, "AAA", "CCC", 5)

        with self.assertRaises(EntityNotFoundError) as ctx:
            route.detach_package(
                package,  # type: ignore[reportArgumentType]
                reason=PackageDetachmentReason.PACKAGE_REMOVED,
                occurred_at=EVENT_TIME,
            )

        self.assertIn("1", str(ctx.exception))
        self.assertNotIn(package, route.packages)
        self.assertIsNone(package.route)

    def test_detach_package_raises_when_assigned_to_different_route(self, *_: object) -> None:
        route_1 = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        route_2 = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=2)
        package = _Pkg(1, "AAA", "CCC", 5)

        route_2.assign_package(package, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]

        with self.assertRaises(EntityNotFoundError) as ctx:
            route_1.detach_package(
                package,  # type: ignore[reportArgumentType]
                reason=PackageDetachmentReason.PACKAGE_REMOVED,
                occurred_at=EVENT_TIME,
            )

        self.assertIn("1", str(ctx.exception))
        self.assertIs(package.route, route_2)
        self.assertIn(package, route_2.packages)
        self.assertNotIn(package, route_1.packages)

    def test_release_truck_releases_and_clears_route_truck(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=1)
        truck = Truck(1, TruckModel.SCANIA, 42000, 8000)
        route.assign_truck(truck, occurred_at=EVENT_TIME)
        route.clear_events()

        released = route.release_truck(
            force=True,
            reason=TruckReleaseReason.ROUTE_REMOVED,
            occurred_at=EVENT_TIME,
        )

        self.assertTrue(released)
        self.assertIsNone(truck.route)
        self.assertIsNone(route.truck)
        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, TruckReleasedFromRoute)
        assert isinstance(event, TruckReleasedFromRoute)
        self.assertEqual(event.route_id, 1)
        self.assertEqual(event.truck_id, 1)
        self.assertEqual(event.release_location, LocationCode("BBB"))
        self.assertEqual(event.reason, TruckReleaseReason.ROUTE_REMOVED)
        self.assertEqual(event.occurred_at, EVENT_TIME)

    def test_release_truck_without_truck_is_noop(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=1)

        released = route.release_truck(
            force=True,
            reason=TruckReleaseReason.ROUTE_REMOVED,
            occurred_at=EVENT_TIME,
        )

        self.assertFalse(released)
        self.assertIsNone(route.truck)
        self.assertEqual(route.pending_events, ())

    def test_release_truck_returns_false_when_truck_reports_no_release(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=1)
        truck = Truck(1, TruckModel.SCANIA, 42000, 8000)
        route.assign_truck(truck, occurred_at=EVENT_TIME)
        route.clear_events()

        def fail_release(*, now: datetime | None = None, force: bool = False) -> bool:
            del now, force
            truck.route = None
            return False

        with patch.object(truck, "release", side_effect=fail_release):
            released = route.release_truck(
                force=True,
                reason=TruckReleaseReason.ROUTE_REMOVED,
                occurred_at=EVENT_TIME,
            )

        self.assertFalse(released)
        self.assertIs(route.truck, truck)
        self.assertEqual(route.pending_events, ())

    def test_release_truck_restores_truck_when_released_location_is_missing(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=1)
        truck = Truck(1, TruckModel.SCANIA, 42000, 8000)
        route.assign_truck(truck, occurred_at=EVENT_TIME)
        route.clear_events()

        def release_without_location(*, now: datetime | None = None, force: bool = False) -> bool:
            del now, force
            truck.route = None
            truck.current_location = None
            return True

        with (
            patch.object(truck, "release", side_effect=release_without_location),
            self.assertRaises(RuntimeError),
        ):
            route.release_truck(
                force=True,
                reason=TruckReleaseReason.ROUTE_REMOVED,
                occurred_at=EVENT_TIME,
            )

        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(route.pending_events, ())

    def test_assign_truck_records_assignment_event(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=1)
        truck = Truck(10, TruckModel.SCANIA, 42000, 8000)

        route.assign_truck(truck, occurred_at=EVENT_TIME)

        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, TruckAssignedToRoute)
        assert isinstance(event, TruckAssignedToRoute)
        self.assertEqual(event.route_id, 1)
        self.assertEqual(event.truck_id, 10)
        self.assertEqual(event.occurred_at, EVENT_TIME)

    def test_assign_truck_rejects_truck_assigned_to_another_route(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=1)
        other_route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=2)
        truck = Truck(10, TruckModel.SCANIA, 42000, 8000)
        other_route.assign_truck(truck, occurred_at=EVENT_TIME)

        with self.assertRaises(DomainConflictError):
            route.assign_truck(truck, occurred_at=EVENT_TIME)

        self.assertIsNone(route.truck)
        self.assertIs(truck.route, other_route)
        self.assertEqual(route.pending_events, ())

    def test_release_truck_before_completion_records_no_event(self, *_: object) -> None:
        departure_time = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute(
            LocationCode("AAA"),
            LocationCode("BBB"),
            departure_time=departure_time,
            route_id=1,
        )
        truck = Truck(10, TruckModel.SCANIA, 42000, 8000)
        route.assign_truck(truck, occurred_at=EVENT_TIME)
        route.clear_events()

        released = route.release_truck(
            now=departure_time,
            force=False,
            reason=TruckReleaseReason.ROUTE_COMPLETED,
            occurred_at=route.eta_final or departure_time,
        )

        self.assertFalse(released)
        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(route.pending_events, ())

    def test_record_removal_records_route_snapshot_identifiers(self, *_: object) -> None:
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), route_id=7)

        route.record_removal(
            detached_package_ids=(11, 12),
            released_truck_id=10,
            occurred_at=EVENT_TIME,
        )

        self.assertEqual(len(route.pending_events), 1)
        event = route.pending_events[0]
        self.assertIsInstance(event, RouteRemoved)
        assert isinstance(event, RouteRemoved)
        self.assertEqual(event.route_id, 7)
        self.assertEqual(event.detached_package_ids, (11, 12))
        self.assertEqual(event.released_truck_id, 10)
        self.assertEqual(event.occurred_at, EVENT_TIME)

    def test_snapshot_state_restores_route_schedule_truck_and_packages(self, *_: object) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute(LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC"), route_id=1)
        package = _Pkg(1, "AAA", "CCC", 5)
        truck = _Truck(route=route)
        route.schedule(base, occurred_at=EVENT_TIME)
        route.assign_package(package, occurred_at=EVENT_TIME)  # type: ignore[reportArgumentType]
        route.truck = truck  # type: ignore[reportAttributeAccessIssue]
        snapshot = route.snapshot_state()

        route.detach_package(
            package,  # type: ignore[reportArgumentType]
            reason=PackageDetachmentReason.PACKAGE_REMOVED,
            occurred_at=EVENT_TIME,
        )
        route.truck = None

        route.restore_state(snapshot)

        self.assertEqual(route.departure_time, base)
        self.assertEqual(route.status, RouteStatus.SCHEDULED)
        self.assertIs(route.truck, truck)
        self.assertEqual(route.packages, (package,))
        self.assertEqual(route.arrival_time_at(LocationCode("AAA")), base)