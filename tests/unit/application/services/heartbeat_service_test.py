import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.services.heartbeat_service import HeartbeatService
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.truck_status import TruckStatus


class _FakeTruck:
    def __init__(self, current_location: str = "BASE") -> None:
        self.current_location = current_location
        self.in_transit_to: str | None = None
        self.route: _FakeRoute | None = None
        self.status = TruckStatus.ON_THE_WAY
        self.busy_from = None
        self.busy_until = None

    def release(self, now: datetime | None = None, force: bool = False) -> bool:
        if self.route is None:
            self.status = TruckStatus.FREE
            self.in_transit_to = None
            self.busy_from = None
            self.busy_until = None
            return False

        eta = self.route.eta_final
        if not force and (eta is None or now is None or now < eta):
            return False

        self.current_location = self.route.end_location
        self.route = None
        self.status = TruckStatus.FREE
        self.in_transit_to = None
        self.busy_from = None
        self.busy_until = None
        return True


class _FakePackage:
    def __init__(self, start: str, end: str) -> None:
        self.start_location = start
        self.end_location = end
        self.current_location = start
        self.expected_arrival = None
        self.status: ItemStatus | None = None


class _FakeRoute:
    def __init__(
        self,
        *,
        locations: list[str],
        departure_time: datetime | None,
        eta_final: datetime | None,
        packages: list[_FakePackage] | None = None,
    ) -> None:
        self.locations = locations
        self.start_location = locations[0]
        self.end_location = locations[-1]
        self.departure_time = departure_time
        self.eta_final = eta_final
        self.truck: _FakeTruck | None = None
        self.packages = packages or []
        self.status: str | None = None

    def current_position(self, now: datetime) -> SimpleNamespace:
        if self.departure_time is None:
            return SimpleNamespace(kind="UNSCHEDULED")
        if now < self.departure_time:
            return SimpleNamespace(kind="BEFORE_START")
        if self.eta_final and now >= self.eta_final:
            return SimpleNamespace(kind="AFTER_END")

        for city in self.locations:
            arrival = self.arrival_time_at(city)
            if now == arrival:
                return SimpleNamespace(kind="AT_STOP", stop_city=city)
            if now < arrival:
                prev_index = max(self.locations.index(city) - 1, 0)
                return SimpleNamespace(
                    kind="IN_TRANSIT",
                    from_city=self.locations[prev_index],
                    to_city=city,
                )

        return SimpleNamespace(kind="AT_STOP", stop_city=self.end_location)

    def arrival_time_at(self, city: str) -> datetime:
        if self.departure_time is None:
            raise ValueError("unscheduled")
        return self.departure_time + timedelta(hours=self.locations.index(city))

    def release_truck(self, *, now: datetime | None = None, force: bool = False) -> bool:
        if self.truck is None:
            return False

        truck = self.truck
        released = truck.release(now=now, force=force)
        if released or truck.route is None:
            self.truck = None
        return released


class HeartbeatServiceTests(unittest.TestCase):
    def test_advance_updates_route_statuses_truck_positions_and_packages(self) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        package_mid = _FakePackage("S3", "M3")
        package_end = _FakePackage("S3", "E3")

        scheduled_route = _FakeRoute(
            locations=["S1", "E1"],
            departure_time=base + timedelta(hours=2),
            eta_final=base + timedelta(hours=3),
        )
        scheduled_truck = _FakeTruck(current_location="X")
        scheduled_route.truck = scheduled_truck
        scheduled_truck.route = scheduled_route

        in_progress_route = _FakeRoute(
            locations=["S3", "M3", "E3"],
            departure_time=base,
            eta_final=base + timedelta(hours=2),
            packages=[package_mid, package_end],
        )
        in_progress_truck = _FakeTruck(current_location="S3")
        in_progress_route.truck = in_progress_truck
        in_progress_truck.route = in_progress_route

        unscheduled_route = _FakeRoute(
            locations=["S4", "E4"],
            departure_time=None,
            eta_final=None,
        )

        routes = [scheduled_route, in_progress_route, unscheduled_route]
        route_repo = MagicMock()
        route_repo.list_all.return_value = routes

        service = HeartbeatService(route_repo, WorldStateReconciliationService())

        summary_before_departure = service.advance(now=base)
        summary_mid_route = service.advance(now=base + timedelta(minutes=30))

        self.assertEqual(summary_before_departure.routes_updated, 3)
        self.assertEqual(summary_before_departure.packages_updated, 2)
        self.assertTrue(summary_before_departure.state_changed)

        self.assertEqual(scheduled_route.status, "SCHEDULED")
        self.assertEqual(in_progress_route.status, "IN_PROGRESS")
        self.assertEqual(unscheduled_route.status, "PLANNED")
        self.assertEqual(scheduled_truck.current_location, "S1")

        self.assertEqual(summary_mid_route.routes_updated, 0)
        self.assertEqual(summary_mid_route.packages_updated, 0)
        self.assertEqual(summary_mid_route.trucks_moved, 1)
        self.assertTrue(summary_mid_route.state_changed)

        self.assertEqual(in_progress_truck.current_location, "S3")
        self.assertEqual(in_progress_truck.in_transit_to, "M3")
        self.assertEqual(package_mid.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(package_end.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(package_mid.current_location, "S3")
        self.assertEqual(package_end.current_location, "S3")
        self.assertEqual(package_mid.expected_arrival, in_progress_route.arrival_time_at("M3"))
        self.assertEqual(package_end.expected_arrival, in_progress_route.arrival_time_at("E3"))

    def test_advance_releases_truck_and_marks_packages_done_after_completion(self) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        package = _FakePackage("S3", "E3")
        route = _FakeRoute(
            locations=["S3", "M3", "E3"],
            departure_time=base,
            eta_final=base + timedelta(hours=2),
            packages=[package],
        )
        truck = _FakeTruck(current_location="M3")
        route.truck = truck
        truck.route = route

        route_repo = MagicMock()
        route_repo.list_all.return_value = [route]

        service = HeartbeatService(route_repo, WorldStateReconciliationService())

        summary = service.advance(now=base + timedelta(hours=2))

        self.assertEqual(summary.routes_updated, 1)
        self.assertEqual(summary.trucks_released, 1)
        self.assertEqual(summary.trucks_moved, 1)
        self.assertTrue(summary.state_changed)
        self.assertEqual(summary.packages_updated, 1)
        self.assertEqual(route.status, "COMPLETED")
        self.assertIsNone(route.truck)
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertEqual(truck.current_location, "E3")
        self.assertEqual(package.status, ItemStatus.DONE)
        self.assertEqual(package.current_location, "E3")

    def test_advance_reports_state_changed_for_expected_arrival_only_update(self) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        package = _FakePackage("S3", "E3")
        package.status = ItemStatus.IN_PROGRESS
        route = _FakeRoute(
            locations=["S3", "M3", "E3"],
            departure_time=base,
            eta_final=base + timedelta(hours=2),
            packages=[package],
        )
        route.status = "IN_PROGRESS"
        truck = _FakeTruck(current_location="S3")
        truck.in_transit_to = "M3"
        route.truck = truck
        truck.route = route

        route_repo = MagicMock()
        route_repo.list_all.return_value = [route]

        service = HeartbeatService(route_repo, WorldStateReconciliationService())

        summary = service.advance(now=base + timedelta(minutes=30))

        self.assertTrue(summary.state_changed)
        self.assertEqual(summary.packages_updated, 1)
        self.assertEqual(package.expected_arrival, route.arrival_time_at("E3"))
