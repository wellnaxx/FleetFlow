from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import NamedTuple
from unittest.mock import MagicMock

from src.application.events.reconciliation_events import TruckRouteReferenceReconciled
from src.application.services.heartbeat_service import HeartbeatService
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_status import TruckStatus


class _FakeTruckSnapshot(NamedTuple):
    current_location: str
    in_transit_to: str | None
    route: _FakeRoute | None
    status: TruckStatus
    busy_from: object | None
    busy_until: object | None


class _FakeTruck:
    def __init__(self, current_location: str = "BASE", vehicle_id: int = 1) -> None:
        self.vehicle_id = vehicle_id
        self.current_location = current_location
        self.in_transit_to: str | None = None
        self.route: _FakeRoute | None = None
        self.status = TruckStatus.ON_THE_WAY
        self.busy_from = None
        self.busy_until = None

    def snapshot_state(self) -> _FakeTruckSnapshot:
        return _FakeTruckSnapshot(
            current_location=self.current_location,
            in_transit_to=self.in_transit_to,
            route=self.route,
            status=self.status,
            busy_from=self.busy_from,
            busy_until=self.busy_until,
        )

    def restore_state(self, snapshot: _FakeTruckSnapshot) -> None:
        self.current_location = snapshot.current_location
        self.in_transit_to = snapshot.in_transit_to
        self.route = snapshot.route
        self.status = snapshot.status
        self.busy_from = snapshot.busy_from
        self.busy_until = snapshot.busy_until

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


class _FakePackageSnapshot(NamedTuple):
    current_location: str
    expected_arrival: datetime | None
    status: ItemStatus | None


class _FakePackage:
    def __init__(self, start: str, end: str, package_id: int = 1) -> None:
        self.package_id = package_id
        self.start_location = start
        self.end_location = end
        self.current_location = start
        self.expected_arrival = None
        self.status = ItemStatus.TODO
        self._pending_events: list[tuple[str, datetime]] = []

    def snapshot_state(self) -> _FakePackageSnapshot:
        return _FakePackageSnapshot(
            current_location=self.current_location,
            expected_arrival=self.expected_arrival,
            status=self.status,
        )

    def restore_state(self, snapshot: _FakePackageSnapshot) -> None:
        self.current_location = snapshot.current_location
        self.expected_arrival = snapshot.expected_arrival
        self.status = snapshot.status

    def mark_picked_up(self, *, occurred_at: datetime) -> None:
        self.status = ItemStatus.IN_PROGRESS
        self.current_location = self.start_location
        self._pending_events.append(("picked_up", occurred_at))

    def mark_delivered(self, *, occurred_at: datetime) -> None:
        self.status = ItemStatus.DONE
        self.current_location = self.end_location
        self._pending_events.append(("delivered", occurred_at))

    @property
    def pending_events(self) -> tuple[tuple[str, datetime], ...]:
        return tuple(self._pending_events)

    def event_checkpoint(self) -> int:
        return len(self._pending_events)

    def restore_event_checkpoint(self, checkpoint: int) -> None:
        del self._pending_events[checkpoint:]


class _FakeRouteSnapshot(NamedTuple):
    truck: _FakeTruck | None
    packages: tuple[_FakePackage, ...]
    status: RouteStatus | None


class _FakeRoute:
    def __init__(
        self,
        *,
        locations: list[str],
        departure_time: datetime | None,
        eta_final: datetime | None,
        packages: list[_FakePackage] | None = None,
        route_id: int = 1,
    ) -> None:
        self.route_id = route_id
        self.locations = locations
        self.start_location = locations[0]
        self.end_location = locations[-1]
        self.departure_time = departure_time
        self.eta_final = eta_final
        self.truck: _FakeTruck | None = None
        self.packages = packages or []
        self.status: RouteStatus | None = None
        self._pending_events: list[tuple[str, datetime]] = []

    def snapshot_state(self) -> _FakeRouteSnapshot:
        return _FakeRouteSnapshot(
            truck=self.truck,
            packages=tuple(self.packages),
            status=self.status,
        )

    def restore_state(self, snapshot: _FakeRouteSnapshot) -> None:
        self.truck = snapshot.truck
        self.packages = list(snapshot.packages)
        self.status = snapshot.status

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

    def mark_started(self, *, occurred_at: datetime) -> None:
        self.status = RouteStatus.IN_PROGRESS
        self._pending_events.append(("started", occurred_at))

    def mark_completed(self, *, occurred_at: datetime) -> None:
        self.status = RouteStatus.COMPLETED
        self._pending_events.append(("completed", occurred_at))

    def event_checkpoint(self) -> int:
        return len(self._pending_events)

    def restore_event_checkpoint(self, checkpoint: int) -> None:
        del self._pending_events[checkpoint:]

    def release_truck(
        self,
        *,
        now: datetime | None = None,
        force: bool = False,
        reason: object,
        occurred_at: datetime,
    ) -> bool:
        del reason, occurred_at
        if self.truck is None:
            return False

        truck = self.truck
        released = truck.release(now=now, force=force)
        if released or truck.route is None:
            self.truck = None
        return released


def _unit_of_work_mock() -> MagicMock:
    unit_of_work = MagicMock()
    unit_of_work.__enter__.return_value = unit_of_work
    unit_of_work.__exit__.return_value = False
    return unit_of_work


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
        unit_of_work = _unit_of_work_mock()

        service = HeartbeatService(route_repo, WorldStateReconciliationService(), unit_of_work)

        summary_before_departure = service.advance(now=base)
        summary_mid_route = service.advance(now=base + timedelta(minutes=30))

        self.assertEqual(summary_before_departure.routes_updated, 3)
        self.assertEqual(summary_before_departure.packages_updated, 2)
        self.assertTrue(summary_before_departure.state_changed)

        self.assertEqual(scheduled_route.status, RouteStatus.SCHEDULED)
        self.assertEqual(in_progress_route.status, RouteStatus.IN_PROGRESS)
        self.assertEqual(unscheduled_route.status, RouteStatus.PLANNED)
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
        self.assertEqual(unit_of_work.commit.call_count, 2)
        self.assertEqual(unit_of_work.routes.update_state.call_count, 3)
        self.assertEqual(unit_of_work.packages.update_state.call_count, 2)
        self.assertEqual(unit_of_work.trucks.update_state.call_count, 2)

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
        unit_of_work = _unit_of_work_mock()

        service = HeartbeatService(route_repo, WorldStateReconciliationService(), unit_of_work)

        summary = service.advance(now=base + timedelta(hours=2))

        self.assertEqual(summary.routes_updated, 1)
        self.assertEqual(summary.trucks_released, 1)
        self.assertEqual(summary.trucks_moved, 1)
        self.assertTrue(summary.state_changed)
        self.assertEqual(summary.packages_updated, 1)
        self.assertEqual(route.status, RouteStatus.COMPLETED)
        self.assertIsNone(route.truck)
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertEqual(truck.current_location, "E3")
        self.assertEqual(package.status, ItemStatus.DONE)
        self.assertEqual(package.current_location, "E3")
        unit_of_work.routes.update_state.assert_called_once_with(route)
        unit_of_work.packages.update_state.assert_called_once_with(package)
        unit_of_work.trucks.update_state.assert_called_once_with(truck)
        unit_of_work.commit.assert_called_once_with()

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
        route.status = RouteStatus.IN_PROGRESS
        truck = _FakeTruck(current_location="S3")
        truck.in_transit_to = "M3"
        route.truck = truck
        truck.route = route

        route_repo = MagicMock()
        route_repo.list_all.return_value = [route]
        unit_of_work = _unit_of_work_mock()

        service = HeartbeatService(route_repo, WorldStateReconciliationService(), unit_of_work)

        summary = service.advance(now=base + timedelta(minutes=30))

        self.assertTrue(summary.state_changed)
        self.assertEqual(summary.packages_updated, 1)
        self.assertEqual(package.expected_arrival, route.arrival_time_at("E3"))
        unit_of_work.routes.update_state.assert_not_called()
        unit_of_work.packages.update_state.assert_called_once_with(package)
        unit_of_work.trucks.update_state.assert_not_called()
        unit_of_work.commit.assert_called_once_with()

    def test_advance_persists_repaired_truck_route_reference(self) -> None:
        route = _FakeRoute(
            locations=["S1", "E1"],
            departure_time=None,
            eta_final=None,
        )
        route.status = RouteStatus.PLANNED
        truck = _FakeTruck(current_location="S1")
        route.truck = truck
        truck.route = None

        route_repo = MagicMock()
        route_repo.list_all.return_value = [route]
        unit_of_work = _unit_of_work_mock()
        service = HeartbeatService(route_repo, WorldStateReconciliationService(), unit_of_work)

        summary = service.advance(now=datetime(2025, 1, 1, 8, 0))

        self.assertIs(truck.route, route)
        self.assertEqual(summary.trucks_reconciled, 1)
        self.assertTrue(summary.state_changed)
        self.assertEqual(len(summary.reconciliation_events), 1)
        self.assertIsInstance(
            summary.reconciliation_events[0],
            TruckRouteReferenceReconciled,
        )
        unit_of_work.trucks.update_state.assert_called_once_with(truck)
        unit_of_work.commit.assert_called_once_with()

    def test_advance_persists_healthy_route_when_another_route_fails_reconciliation(self) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        conflicting_route = _FakeRoute(
            locations=["S1", "E1"],
            departure_time=base,
            eta_final=base + timedelta(hours=1),
            route_id=1,
        )
        corrupted_route = _FakeRoute(
            locations=["S2", "E2"],
            departure_time=None,
            eta_final=None,
            route_id=2,
        )
        healthy_route = _FakeRoute(
            locations=["S3", "E3"],
            departure_time=None,
            eta_final=None,
            route_id=3,
        )
        truck = _FakeTruck(vehicle_id=1001)
        truck.route = conflicting_route
        corrupted_route.truck = truck
        corrupted_route.status = RouteStatus.IN_PROGRESS
        healthy_route.status = RouteStatus.IN_PROGRESS
        route_repo = MagicMock()
        route_repo.list_all.return_value = [corrupted_route, healthy_route]
        unit_of_work = _unit_of_work_mock()
        service = HeartbeatService(route_repo, WorldStateReconciliationService(), unit_of_work)

        with self.assertLogs(
            "src.application.services.world_state_reconciliation_service",
            level="ERROR",
        ):
            summary = service.advance(now=base)

        self.assertEqual(corrupted_route.status, RouteStatus.IN_PROGRESS)
        self.assertIs(corrupted_route.truck, truck)
        self.assertIs(truck.route, conflicting_route)
        self.assertEqual(healthy_route.status, RouteStatus.PLANNED)
        self.assertEqual(summary.mutated_routes, (healthy_route,))
        unit_of_work.routes.update_state.assert_called_once_with(healthy_route)
        unit_of_work.commit.assert_called_once_with()

    def test_advance_skips_unit_of_work_when_reconciliation_changes_nothing(self) -> None:
        route = _FakeRoute(
            locations=["S1", "E1"],
            departure_time=None,
            eta_final=None,
        )
        route.status = RouteStatus.PLANNED

        route_repo = MagicMock()
        route_repo.list_all.return_value = [route]
        unit_of_work = _unit_of_work_mock()

        service = HeartbeatService(route_repo, WorldStateReconciliationService(), unit_of_work)

        summary = service.advance(now=datetime(2025, 1, 1, 8, 0))

        self.assertFalse(summary.state_changed)
        unit_of_work.__enter__.assert_not_called()
        unit_of_work.commit.assert_not_called()

    def test_advance_restores_domain_state_when_persistence_fails(self) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        package = _FakePackage("S3", "E3")
        route = _FakeRoute(
            locations=["S3", "E3"],
            departure_time=base + timedelta(hours=2),
            eta_final=base + timedelta(hours=3),
            packages=[package],
        )
        truck = _FakeTruck(current_location="X")
        route.truck = truck
        truck.route = route

        route_snapshot = route.snapshot_state()
        package_snapshot = package.snapshot_state()
        truck_snapshot = truck.snapshot_state()

        route_repo = MagicMock()
        route_repo.list_all.return_value = [route]
        unit_of_work = _unit_of_work_mock()
        unit_of_work.packages.update_state.side_effect = RuntimeError("write failed")

        service = HeartbeatService(route_repo, WorldStateReconciliationService(), unit_of_work)

        with self.assertRaisesRegex(RuntimeError, "write failed"):
            service.advance(now=base)

        self.assertEqual(route.snapshot_state(), route_snapshot)
        self.assertEqual(package.snapshot_state(), package_snapshot)
        self.assertEqual(truck.snapshot_state(), truck_snapshot)
        unit_of_work.routes.update_state.assert_called_once_with(route)
        unit_of_work.packages.update_state.assert_called_once_with(package)
        unit_of_work.commit.assert_not_called()

    def test_advance_restores_package_event_checkpoint_when_persistence_fails(self) -> None:
        base = datetime(2025, 1, 1, 8, 0)
        package = _FakePackage("S3", "E3")
        package._pending_events.append(("created", base - timedelta(hours=1))) # pyright: ignore[reportPrivateUsage]
        route = _FakeRoute(
            locations=["S3", "E3"],
            departure_time=base,
            eta_final=base + timedelta(hours=1),
            packages=[package],
        )
        route_repo = MagicMock()
        route_repo.list_all.return_value = [route]
        unit_of_work = _unit_of_work_mock()
        unit_of_work.packages.update_state.side_effect = RuntimeError("write failed")
        service = HeartbeatService(route_repo, WorldStateReconciliationService(), unit_of_work)

        with self.assertRaisesRegex(RuntimeError, "write failed"):
            service.advance(now=base)

        self.assertEqual(package.status, ItemStatus.TODO)
        self.assertEqual(
            package.pending_events,
            (("created", base - timedelta(hours=1)),),
        )
