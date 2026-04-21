# application_data_test.py
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

from src.adapters.driven.persistence.application_data.customer_repository import (
    ApplicationDataCustomerRepository,
)
from src.adapters.driven.persistence.application_data.package_repository import ApplicationDataPackageRepository
from src.adapters.driven.persistence.application_data.route_repository import ApplicationDataRouteRepository
from src.application.services.customer_service import CustomerService
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Role
from src.domain.enums.item_status import ItemStatus


def make_create_route_uc(app: ApplicationData):
    route_repo = ApplicationDataRouteRepository(app)
    return CreateRouteUseCase(route_repo)


def make_view_all_routes_uc(app: ApplicationData):
    route_repo = ApplicationDataRouteRepository(app)
    return ViewAllRoutesUseCase(route_repo)


def make_view_route_uc(app: ApplicationData):
    route_repo = ApplicationDataRouteRepository(app)
    return ViewRouteUseCase(route_repo)


def make_remove_route_uc(app: ApplicationData):
    route_repo = ApplicationDataRouteRepository(app)
    return RemoveRouteUseCase(route_repo)


def make_remove_package_uc(app: ApplicationData):
    package_repo = ApplicationDataPackageRepository(app)
    return RemovePackageUseCase(package_repo)


def make_create_package_uc(app: ApplicationData) -> CreatePackageUseCase:
    customer_repo = ApplicationDataCustomerRepository(app)
    package_repo = ApplicationDataPackageRepository(app)
    customer_service = CustomerService(customer_repo)
    return CreatePackageUseCase(customer_service, package_repo)


def make_assign_truck_to_route_uc(app: ApplicationData) -> AssignTruckToRouteUseCase:
    route_repo = ApplicationDataRouteRepository(app)
    return AssignTruckToRouteUseCase(route_repo, app.vehicle_manager)


def _mk_app() -> Any:
    """ApplicationData with permissive authz and a stubbed vehicle manager."""
    app = ApplicationData(current_user=None)
    app.authz = SimpleNamespace(  # type: ignore[assignment]
        has=lambda *args: True,  # type: ignore[reportUnknownLambdaType]
        has_all=lambda *args: True,  # type: ignore[reportUnknownLambdaType]
    )
    app.vehicle_manager = MagicMock()  # type: ignore[assignment]
    app.vehicle_manager.vehicles = []
    return app


def _fake_delivery_route_ctor(
    *locs: str,
    departure_time: datetime | None = None,
    route_id: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        route_id=route_id,
        locations=list(locs),
        start_location=locs[0],
        end_location=locs[-1],
        departure_time=departure_time,
        packages=[],
        truck=None,
    )


def _location_is_not_bad(location: str) -> bool:
    return location != "BAD"


# ---------------------------
# Lightweight fakes for route/truck/pkg where helpful
# ---------------------------


class _FakeTruck:
    def __init__(self, vehicle_id: int = 1, capacity: float = 100.0, current_location: str = "BASE") -> None:
        self.vehicle_id = vehicle_id
        self.capacity = capacity
        self.current_location = current_location
        self.in_transit_to: str | None = None
        self.route: Any = None

    def assign(self, route: Any, start_loc: str) -> bool:
        self.route = route
        self.current_location = start_loc
        return True

    def release(self, now: datetime | None = None, force: bool = False) -> bool:
        released = self.route is not None
        self.route = None
        self.in_transit_to = None
        return released


class _FakeRoute:
    def __init__(
        self,
        route_id: int,
        locations: list[str],
        departure_time: datetime | None = None,
        eta_final: datetime | None = None,
    ) -> None:
        self.route_id = route_id
        self.locations = list(locations)
        self.start_location = locations[0]
        self.end_location = locations[-1]
        self.departure_time = departure_time
        self.eta_final = eta_final
        self.truck: _FakeTruck | None = None
        self.packages: list[Any] = []
        self.status: str | None = None

    def schedule(self, when: datetime) -> None:
        self.departure_time = when

    def total_assigned_weight(self) -> float:
        return sum(getattr(p, "weight", 0.0) for p in self.packages)

    def assign_package(self, pkg: Any) -> None:
        self.packages.append(pkg)
        pkg.route = self

    def detach_package(self, package: Any) -> None:
        for i, existing in enumerate(self.packages):
            if existing.package_id == package.package_id:
                self.packages.pop(i)
                if getattr(package, "route", None) is self:
                    package.route = None
                return
        raise ValueError(f"Package with id {package.package_id} is not assigned to this route.")

    def arrival_time_at(self, city: str) -> datetime:
        idx = self.locations.index(city)
        if self.departure_time is None:
            raise ValueError("unscheduled")
        return self.departure_time + timedelta(hours=idx)

    def current_position(self, now: datetime) -> SimpleNamespace:
        if self.departure_time is None:
            return SimpleNamespace(kind="UNSCHEDULED")
        if now < self.departure_time:
            return SimpleNamespace(kind="BEFORE_START")
        if self.eta_final and now >= self.eta_final:
            return SimpleNamespace(kind="AFTER_END")
        for i, city in enumerate(self.locations):
            t = self.arrival_time_at(city)
            if abs((now - t).total_seconds()) < 1e-6:
                return SimpleNamespace(kind="AT_STOP", stop_city=city)
            if now < t:
                prev = self.locations[i - 1] if i > 0 else self.start_location
                return SimpleNamespace(
                    kind="IN_TRANSIT",
                    from_city=prev,
                    to_city=city,
                    next_eta=self.arrival_time_at(city),
                )
        return SimpleNamespace(kind="AT_STOP", stop_city=self.end_location)


class _FakePackage:
    def __init__(
        self, package_id: int, start: str, end: str, weight: float = 1.0, customer: Any = None
    ) -> None:
        self.package_id = package_id
        self.start_location = start
        self.end_location = end
        self.weight = weight
        self.customer: Any = customer or SimpleNamespace(customer_id=1)
        self.route: Any = None
        self.status: str | None = None


# ---------------------------
# Tests
# ---------------------------


class ApplicationData_CreateRemove_Should(unittest.TestCase):
    @patch("src.application.use_cases.routes.create_route.Map.is_valid_location", return_value=True)
    def test_create_route_find_and_remove(self, _is_valid: MagicMock) -> None:
        app = _mk_app()

        with patch("src.application.use_cases.routes.create_route.DeliveryRoute") as DR:
            DR.side_effect = _fake_delivery_route_ctor

            create_route = make_create_route_uc(app)
            remove_route = make_remove_route_uc(app)

            r = create_route.execute(["A", "B"], None)
            self.assertIs(app.find_route(r.route_id), r)

            truck = _FakeTruck(vehicle_id=5)
            r.truck = truck  # type: ignore[reportAttributeAccessIssue]
            truck.route = r

            removed = remove_route.execute(r.route_id)

            self.assertIs(removed, r)
            self.assertIsNone(truck.route)
            self.assertIsNone(app.find_route(r.route_id))

    @patch(
        "src.application.use_cases.routes.create_route.Map.is_valid_location",
        side_effect=_location_is_not_bad,
    )
    def test_create_route_validates_locations(self, is_valid: MagicMock) -> None:
        app = _mk_app()
        create_route = make_create_route_uc(app)

        with self.assertRaises(ValueError):
            create_route.execute(["A"], None)

        with self.assertRaises(ValueError):
            create_route.execute(["A", "BAD"], None)

        with patch("src.application.use_cases.routes.create_route.DeliveryRoute") as DR:
            DR.side_effect = _fake_delivery_route_ctor

            _ = create_route.execute(["A", "B", "C"], None)

    def test_view_routes_and_packages_helpers(self) -> None:
        app = _mk_app()
        r = SimpleNamespace(route_id=1)
        p = SimpleNamespace(package_id=2)
        app._routes = [r]
        app._packages = [p]

        view_all_routes = make_view_all_routes_uc(app)

        self.assertIn(r, app.routes)
        self.assertIn(p, app.packages)
        self.assertIn(r, view_all_routes.execute())
        self.assertIn(p, app.view_all_packages())


class ApplicationData_AssignPackages_Should(unittest.TestCase):
    def _seed_app_with_route_and_packages(
        self,
        scheduled: bool = False,
    ) -> tuple[Any, Any, tuple[Any, Any, Any]]:
        app = _mk_app()
        route = SimpleNamespace(
            route_id=10,
            start_location="SYD",
            end_location="MEL",
            locations=["SYD", "CBR", "MEL"],
            packages=[],
            truck=None,
            departure_time=(datetime(2025, 10, 1, 9, 0) if scheduled else None),
        )

        def arrival_time_at(city: str) -> datetime | None:
            table = {
                "SYD": datetime(2025, 10, 1, 9, 0),
                "CBR": datetime(2025, 10, 1, 12, 0),
                "MEL": datetime(2025, 10, 1, 18, 0),
            }
            return table.get(city)

        route.arrival_time_at = arrival_time_at
        app._routes.append(route)

        pkg1 = SimpleNamespace(package_id=1, end_location="MEL", route=None)
        pkg2 = SimpleNamespace(package_id=2, end_location="CBR", route=None)
        pkg3 = SimpleNamespace(package_id=3, end_location="MEL", route=route)
        app._packages.extend([pkg1, pkg2, pkg3])
        return app, route, (pkg1, pkg2, pkg3)

    def test_assign_packages_unscheduled_route_formats_eta_na(self) -> None:
        app, route, (pkg1, _, _) = self._seed_app_with_route_and_packages(scheduled=False)
        out_parts = app.assign_packages_to_route(route.route_id, [pkg1.package_id])
        self.assertEqual(
            out_parts,
            [f"Assigned package {pkg1.package_id} to route {route.route_id}. ETA: N/A (route unscheduled)"],
        )
        self.assertIs(pkg1.route, route)
        self.assertIn(pkg1, route.packages)

    def test_assign_packages_scheduled_mixes_success_and_errors(self) -> None:
        app, route, (pkg1, _, pkg3) = self._seed_app_with_route_and_packages(scheduled=True)
        out = app.assign_packages_to_route(
            route.route_id,
            [pkg1.package_id, 99, pkg3.package_id, pkg1.package_id],
        )
        txt = "\n".join(out)
        self.assertIn("Assigned package 1 to route 10. ETA: 2025-10-01 18:00", txt)
        self.assertIn("Failed:", txt)
        self.assertIn("Package 99 not found.", txt)
        self.assertIn("already on route 10", txt)

    def test_assign_packages_all_errors_raise(self) -> None:
        app, route, (_, _, pkg3) = self._seed_app_with_route_and_packages(scheduled=True)
        app._packages = [pkg3]
        with self.assertRaises(ValueError) as ctx:
            app.assign_packages_to_route(route.route_id, [999, pkg3.package_id])
        self.assertIn("No packages could be assigned:", str(ctx.exception))


class ApplicationData_FindSuitables_Should(unittest.TestCase):
    def test_find_suitable_routes_for_package_capacity_and_sort(self) -> None:
        app = _mk_app()
        r1 = _FakeRoute(
            10,
            ["A", "B", "C"],
            departure_time=datetime(2025, 1, 1, 8),
            eta_final=datetime(2025, 1, 1, 10),
        )
        r2 = _FakeRoute(
            20,
            ["A", "X", "C"],
            departure_time=datetime(2025, 1, 1, 9),
            eta_final=datetime(2025, 1, 1, 11),
        )
        r3 = _FakeRoute(30, ["A", "C"])  # unscheduled
        t1 = _FakeTruck(vehicle_id=100, capacity=5.0)
        t2 = _FakeTruck(vehicle_id=200, capacity=1.0)  # too small
        r1.truck = t1
        r2.truck = t2

        app._routes = [r3, r2, r1]
        cust = SimpleNamespace(customer_id=1)
        pkg = _FakePackage(7, "A", "C", weight=2.0, customer=cust)
        app._packages = [pkg]

        res = app.find_suitable_routes_for_package(pkg.package_id)
        ids = [x["route"].route_id for x in res]
        self.assertEqual(ids, [10, 30])

    def test_find_suitable_trucks_for_route_delegates(self) -> None:
        app = _mk_app()
        r = _FakeRoute(9, ["A", "B"])
        app._routes = [r]
        app.vehicle_manager.find_available_for_route.return_value = ["T1", "T2"]
        out = app.find_suitable_trucks_for_route(9)
        self.assertEqual(out, ["T1", "T2"])
        app.vehicle_manager.find_available_for_route.assert_called_once()


class ApplicationData_AssignTruckAndHeartbeat_Should(unittest.TestCase):
    def test_assign_truck_schedules_if_unscheduled_and_checks_suitability(self) -> None:
        app = _mk_app()
        r = _FakeRoute(1, ["S", "E"])  # unscheduled initially
        app._routes = [r]

        truck = _FakeTruck(vehicle_id=5, capacity=10.0)
        app.vehicle_manager.find_by_id.return_value = truck
        app.vehicle_manager.is_suitable_for_route.return_value = (True, "")

        assign_truck = make_assign_truck_to_route_uc(app)
        now = datetime(2025, 1, 1, 10, 0)

        result = assign_truck.execute(5, 1, now=now)

        self.assertIs(result, r)
        self.assertIs(r.truck, truck)
        self.assertIs(truck.route, r)
        self.assertEqual(r.departure_time, now)
        app.vehicle_manager.find_by_id.assert_called_once_with(5)
        app.vehicle_manager.is_suitable_for_route.assert_called_once_with(truck, r)

    def test_assign_truck_not_found_errors(self) -> None:
        app = _mk_app()
        r = _FakeRoute(1, ["S", "E"])
        app._routes = [r]
        app.vehicle_manager.find_by_id.return_value = None

        assign_truck = make_assign_truck_to_route_uc(app)

        with self.assertRaises(ValueError) as ctx:
            assign_truck.execute(99, 1, now=datetime(2025, 1, 1, 10, 0))

        self.assertIn("Truck with ID 99 not found", str(ctx.exception))

    def test_assign_truck_route_not_found_errors(self) -> None:
        app = _mk_app()
        assign_truck = make_assign_truck_to_route_uc(app)

        with self.assertRaises(ValueError) as ctx:
            assign_truck.execute(5, 999, now=datetime(2025, 1, 1, 10, 0))

        self.assertIn("Route with ID 999 not found", str(ctx.exception))

    def test_assign_truck_unsuitable_errors(self) -> None:
        app = _mk_app()
        r = _FakeRoute(1, ["S", "E"])
        app._routes = [r]

        truck = _FakeTruck(vehicle_id=5, capacity=10.0)
        app.vehicle_manager.find_by_id.return_value = truck
        app.vehicle_manager.is_suitable_for_route.return_value = (False, "range too short")

        assign_truck = make_assign_truck_to_route_uc(app)

        with self.assertRaises(ValueError) as ctx:
            assign_truck.execute(5, 1, now=datetime(2025, 1, 1, 10, 0))

        self.assertIn("Truck 5 is not suitable for route 1: range too short", str(ctx.exception))

    def test_heartbeat_moves_trucks_and_updates_packages(self) -> None:
        app = _mk_app()
        base = datetime(2025, 1, 1, 8, 0)

        # BEFORE_START
        r1 = _FakeRoute(
            1,
            ["S1", "E1"],
            departure_time=base + timedelta(hours=2),
            eta_final=base + timedelta(hours=3),
        )
        t1 = _FakeTruck(vehicle_id=1)
        r1.truck = t1
        t1.route = r1
        t1.current_location = "X"
        # AT_STOP then AFTER_END
        r2 = _FakeRoute(
            2,
            ["S2", "E2"],
            departure_time=base,
            eta_final=base + timedelta(hours=1),
        )
        t2 = _FakeTruck(vehicle_id=2)
        r2.truck = t2
        t2.route = r2
        # IN_TRANSIT
        r3 = _FakeRoute(
            3,
            ["S3", "M3", "E3"],
            departure_time=base,
            eta_final=base + timedelta(hours=2),
        )
        t3 = _FakeTruck(vehicle_id=3)
        r3.truck = t3
        t3.route = r3
        # UNSCHEDULED
        r4 = _FakeRoute(4, ["S4", "E4"], departure_time=None, eta_final=None)

        cust = SimpleNamespace(customer_id=1)
        p_a = _FakePackage(1, "S3", "M3", weight=1, customer=cust)
        p_b = _FakePackage(2, "S3", "E3", weight=1, customer=cust)
        r3.assign_package(p_a)
        r3.assign_package(p_b)

        app._routes = [r1, r2, r3, r4]
        app.vehicle_manager.vehicles = [t1, t2, t3]
        app._packages += [p_a, p_b]

        # 1) exactly departure for r2 -> AT_STOP
        summary1 = app.heartbeat(now=base)
        self.assertGreaterEqual(summary1["trucks_moved"], 0)

        # 2) IN_TRANSIT on r3 between S3->M3 (now S3->M3, should set in_transit_to and count a move)
        mid = base + timedelta(minutes=30)
        summary2 = app.heartbeat(now=mid)
        self.assertGreaterEqual(summary2["trucks_moved"], 1)
        self.assertEqual(p_a.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(p_b.status, ItemStatus.IN_PROGRESS)

        # 3) AFTER_END triggers release on r2
        summary3 = app.heartbeat(now=base + timedelta(hours=2))
        self.assertGreaterEqual(summary3["trucks_released"], 1)

        # route status helper sanity
        self.assertIn(app._compute_route_status(r4, base), {"PLANNED"})
        self.assertEqual(app._compute_route_status(r1, base + timedelta(hours=1)), "SCHEDULED")
        self.assertEqual(app._compute_route_status(r3, base + timedelta(hours=3)), "COMPLETED")


class ApplicationData_SaveLoad_Should(unittest.TestCase):
    @patch("src.core.application_data.resolve_data_path", return_value="C:/fake/state.json")
    @patch("src.core.application_data.os.path.exists", return_value=True)
    @patch("src.core.application_data.open", new_callable=mock_open)
    @patch("src.core.application_data.json.load")
    def test_load_reads_and_applies(
        self,
        mock_json_load: MagicMock,
        m_open: MagicMock,
        _exists: MagicMock,
        _resolve: MagicMock,
    ) -> None:
        app = _mk_app()
        payload = {
            "schema_version": 1,
            "counters": {"next_customer_id": 2, "next_package_id": 3, "next_route_id": 4},
            "customers": [{"customer_id": 1, "name": "Name", "email": "", "phone": ""}],
            "packages": [
                {
                    "package_id": 1,
                    "start": "SYD",
                    "end": "MEL",
                    "weight": 1.0,
                    "customer_id": 1,
                    "route_id": None,
                }
            ],
            "routes": [
                {
                    "route_id": 10,
                    "locations": ["SYD", "MEL"],
                    "departure_time": None,
                    "truck_vehicle_id": None,
                    "package_ids": [],
                }
            ],
        }
        mock_json_load.return_value = payload

        with (
            patch("src.domain.value_objects.contact_info.ContactInfo") as CI,
            patch("src.core.application_data.Customer") as Cust,
            patch("src.core.application_data.DeliveryPackage") as DP,
            patch("src.core.application_data.DeliveryRoute") as DR,
            patch.object(app, "heartbeat", return_value={}),
        ):
            cust_obj = SimpleNamespace(
                customer_id=1,
                name="Name",
                email="",
                phone_number="",
                add_package=lambda p: None,  # type: ignore[reportUnknownLambdaType]
            )
            Cust.side_effect = lambda customer_id, contact: cust_obj  # type: ignore[reportUnknownLambdaType]
            CI.side_effect = lambda name, email, phone_number: SimpleNamespace(  # type: ignore[reportUnknownLambdaType]
                name=name,
                email=email,
                phone_number=phone_number,
            )
            pkg_obj = SimpleNamespace(
                package_id=1,
                start_location="SYD",
                end_location="MEL",
                weight=1.0,
                customer=cust_obj,
            )
            DP.side_effect = lambda *args, **kwargs: pkg_obj  # type: ignore[reportUnknownLambdaType]
            DR.side_effect = lambda *args, **kwargs: SimpleNamespace(  # type: ignore[reportUnknownLambdaType]
                route_id=10,
                locations=["SYD", "MEL"],
                packages=[],
            )

            msg = app.load("state.json")
            self.assertIn("Loaded state from", msg)
            self.assertTrue(app._customers)
            self.assertTrue(app._packages)
            self.assertTrue(app._routes)

    @patch("src.core.application_data.resolve_data_path", return_value="C:/fake/missing.json")
    @patch("src.core.application_data.os.path.exists", return_value=False)
    def test_load_missing_raises(self, _exists: MagicMock, _resolve: MagicMock) -> None:
        app = _mk_app()
        with self.assertRaises(ValueError):
            app.load("missing.json")

    @patch("src.core.application_data.resolve_data_path", return_value="C:/fake/state.json")
    @patch("src.core.application_data.tempfile.mkstemp", return_value=(123, "C:/fake/.appstate.tmp.json"))
    @patch("src.core.application_data.os.fdopen")
    @patch("src.core.application_data.os.replace")
    @patch("src.core.application_data.os.path.dirname", return_value="C:/fake")
    @patch("src.core.application_data.os.makedirs")
    def test_persist_to_file_writes_atomically(
        self,
        makedirs: MagicMock,
        dirname: MagicMock,
        replace: MagicMock,
        fdopen: MagicMock,
        mkstemp: MagicMock,
        resolve: MagicMock,
    ) -> None:
        app = _mk_app()
        with patch.object(app, "_dump_state", return_value={"ok": True}):
            cm = MagicMock()
            fdopen.return_value.__enter__.return_value = cm
            path = app._persist_to_file("state.json")
            self.assertEqual(path, "C:/fake/state.json")
            makedirs.assert_called_once()  # type: ignore[reportUnknownMemberType]
            replace.assert_called_once()  # type: ignore[reportUnknownMemberType]  # atomic rename

    def test_register_user_delegates(self) -> None:
        app = _mk_app()
        auth = MagicMock()
        app.register_user(
            username="u",
            role=Role.EMPLOYEE,
            name="N",
            email="",
            phone="",
            password="pw",
            auth_service=auth,
        )
        auth.register_user.assert_called_once_with(
            username="u", role=Role.EMPLOYEE, name="N", email="", phone_number="", password="pw"
        )


# ---------------------------------------------------------------------------
# Characterization tests – document behaviour of fragile code paths
# ---------------------------------------------------------------------------


class Characterization_PackageRemovalDetach_Should(unittest.TestCase):
    """Package removal must detach the package from routes and registry."""

    def test_remove_unassigned_package(self) -> None:
        app = _mk_app()
        pkg = _FakePackage(1, "A", "B")
        app._packages.append(pkg)
        remove_uc = make_remove_package_uc(app)
        removed = remove_uc.execute(pkg.package_id)
        self.assertIs(removed, pkg)
        self.assertEqual(len(app._packages), 0)

    def test_remove_assigned_clears_route_list(self) -> None:
        app = _mk_app()
        route = _FakeRoute(10, ["A", "B"])
        pkg = _FakePackage(1, "A", "B")
        route.packages.append(pkg)
        pkg.route = route
        app._routes.append(route)
        app._packages.append(pkg)

        remove_uc = make_remove_package_uc(app)
        remove_uc.execute(pkg.package_id)

        self.assertNotIn(pkg, route.packages)

    def test_remove_assigned_sets_route_to_none(self) -> None:
        app = _mk_app()
        route = _FakeRoute(10, ["A", "B"])
        pkg = _FakePackage(1, "A", "B")
        route.packages.append(pkg)
        pkg.route = route
        app._routes.append(route)
        app._packages.append(pkg)

        remove_uc = make_remove_package_uc(app)
        remove_uc.execute(pkg.package_id)
        self.assertIsNone(pkg.route)

    def test_remove_leaves_other_packages_on_route(self) -> None:
        app = _mk_app()
        route = _FakeRoute(10, ["A", "B"])
        pkg1 = _FakePackage(1, "A", "B")
        pkg2 = _FakePackage(2, "A", "B")
        route.packages.extend([pkg1, pkg2])
        pkg1.route = route
        pkg2.route = route
        app._routes.append(route)
        app._packages.extend([pkg1, pkg2])

        remove_uc = make_remove_package_uc(app)
        remove_uc.execute(pkg1.package_id)
        self.assertIn(pkg2, route.packages)
        self.assertIs(pkg2.route, route)


class Characterization_SaveLoadRoundTrip_Should(unittest.TestCase):
    """_dump_state / _apply_state must round-trip all domain entities."""

    def test_round_trip_preserves_counters(self) -> None:
        app = _mk_app()
        create_route = make_create_route_uc(app)
        create_route.execute(["SYD", "MEL"], departure_time=None)

        create_package = make_create_package_uc(app)
        create_package.execute("SYD", "MEL", 5.0, "Alice", "a@test.com")

        state = app._dump_state()

        app2 = _mk_app()
        app2._apply_state(state)
        self.assertEqual(app2._next_customer_id, app._next_customer_id)
        self.assertEqual(app2._next_package_id, app._next_package_id)
        self.assertEqual(app2._next_route_id, app._next_route_id)

    def test_round_trip_preserves_customers(self) -> None:
        app = _mk_app()
        uc = make_create_package_uc(app)
        uc.execute("SYD", "MEL", 3.0, "Bob", "bob@test.com")
        state = app._dump_state()

        app2 = _mk_app()
        app2._apply_state(state)
        self.assertEqual(len(app2._customers), 1)
        self.assertEqual(app2._customers[0].name, "Bob")

    def test_round_trip_preserves_routes(self) -> None:
        app = _mk_app()
        create_route = make_create_route_uc(app)
        r = create_route.execute(["SYD", "MEL", "ADL"], departure_time=None)

        state = app._dump_state()

        app2 = _mk_app()
        app2._apply_state(state)
        self.assertEqual(len(app2._routes), 1)
        self.assertEqual(app2._routes[0].route_id, r.route_id)
        self.assertEqual(list(app2._routes[0].locations), ["SYD", "MEL", "ADL"])

    def test_round_trip_preserves_package_route_link(self) -> None:
        app = _mk_app()
        create_route = make_create_route_uc(app)
        route = create_route.execute(["SYD", "MEL"], departure_time=None)

        create_package = make_create_package_uc(app)
        pkg = create_package.execute("SYD", "MEL", 2.0, "Carl", "carl@test.com")

        app.assign_packages_to_route(route.route_id, [pkg.package_id])
        state = app._dump_state()

        app2 = _mk_app()
        app2._apply_state(state)
        self.assertEqual(len(app2._packages), 1)
        self.assertIsNotNone(app2._packages[0].route)
        self.assertEqual(app2._packages[0].route.route_id, route.route_id)

    def test_apply_bad_schema_raises(self) -> None:
        app = _mk_app()
        with self.assertRaises(ValueError):
            app._apply_state({"schema_version": 99})


class Characterization_HeartbeatStatus_Should(unittest.TestCase):
    """heartbeat() must transition route statuses correctly."""

    def _make_route_with_truck(self, dep: datetime, eta: datetime) -> tuple[Any, _FakeRoute, _FakeTruck]:
        app = _mk_app()
        route = _FakeRoute(1, ["A", "B", "C"], departure_time=dep, eta_final=eta)
        truck = _FakeTruck(vehicle_id=1, current_location="A")
        truck.route = route
        route.truck = truck
        app._routes.append(route)
        app.vehicle_manager.vehicles = [truck]
        return app, route, truck

    def test_status_planned_when_no_departure(self) -> None:
        app = _mk_app()
        route = _FakeRoute(1, ["A", "B"])
        app._routes.append(route)
        app.heartbeat(now=datetime(2025, 1, 1))
        self.assertEqual(route.status, "PLANNED")

    def test_status_scheduled_before_departure(self) -> None:
        dep = datetime(2025, 6, 1, 10, 0)
        eta = datetime(2025, 6, 1, 12, 0)
        app, route, _ = self._make_route_with_truck(dep, eta)
        app.heartbeat(now=datetime(2025, 6, 1, 9, 0))
        self.assertEqual(route.status, "SCHEDULED")

    def test_status_in_progress_after_departure_before_eta(self) -> None:
        dep = datetime(2025, 6, 1, 10, 0)
        eta = datetime(2025, 6, 1, 14, 0)
        app, route, _ = self._make_route_with_truck(dep, eta)
        app.heartbeat(now=datetime(2025, 6, 1, 11, 0))
        self.assertEqual(route.status, "IN_PROGRESS")

    def test_status_completed_at_eta(self) -> None:
        dep = datetime(2025, 6, 1, 10, 0)
        eta = datetime(2025, 6, 1, 12, 0)
        app, route, _ = self._make_route_with_truck(dep, eta)
        app.heartbeat(now=datetime(2025, 6, 1, 12, 0))
        self.assertEqual(route.status, "COMPLETED")

    def test_package_transitions_to_done_at_destination(self) -> None:
        dep = datetime(2025, 1, 1, 0, 0)
        eta = datetime(2025, 1, 1, 2, 0)
        app, route, _ = self._make_route_with_truck(dep, eta)
        pkg = _FakePackage(1, "A", "C")
        route.packages.append(pkg)
        pkg.route = route
        app._packages.append(pkg)

        app.heartbeat(now=datetime(2025, 1, 1, 3, 0))
        self.assertEqual(pkg.status, ItemStatus.DONE)

    def test_truck_released_after_eta(self) -> None:
        dep = datetime(2025, 1, 1, 0, 0)
        eta = datetime(2025, 1, 1, 2, 0)
        app, _route, truck = self._make_route_with_truck(dep, eta)
        app.heartbeat(now=datetime(2025, 1, 1, 3, 0))
        self.assertIsNone(truck.route)


class Characterization_RBAC_Should(unittest.TestCase):
    """Protected operations must respect role permissions."""

    def _app_for_role(self, role: Role) -> ApplicationData:
        from src.application.services.authorization import AuthorizationService
        from src.domain.entities.users.employee import Employee
        from src.domain.entities.users.manager import Manager

        user = Employee("Test") if role == Role.EMPLOYEE else Manager("Test")
        app = ApplicationData(current_user=user)
        app.authz = AuthorizationService(user)
        return app

    def test_employee_cannot_save_state(self) -> None:
        app = self._app_for_role(Role.EMPLOYEE)
        with self.assertRaises(PermissionError):
            app.save("dummy.json")

    def test_employee_cannot_load_state(self) -> None:
        app = self._app_for_role(Role.EMPLOYEE)
        with self.assertRaises(PermissionError):
            app.load("dummy.json")

    def test_employee_cannot_view_all_packages(self) -> None:
        app = self._app_for_role(Role.EMPLOYEE)
        with self.assertRaises(PermissionError):
            app.view_all_packages()

    def test_employee_cannot_view_all_customers(self) -> None:
        app = self._app_for_role(Role.EMPLOYEE)
        with self.assertRaises(PermissionError):
            app.view_all_customers()

    def test_manager_can_save_state(self) -> None:
        app = self._app_for_role(Role.MANAGER)
        with patch.object(app, "_persist_to_file", return_value="/fake/path"):
            result = app.save("state.json")
            self.assertIn("/fake/path", result)

    def test_manager_can_view_all_packages(self) -> None:
        app = self._app_for_role(Role.MANAGER)
        result = app.view_all_packages()
        self.assertEqual(result, ())
