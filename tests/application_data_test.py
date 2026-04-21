import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

from src.adapters.driven.persistence.application_data.customer_repository import (
    ApplicationDataCustomerRepository,
)
from src.adapters.driven.persistence.application_data.package_repository import (
    ApplicationDataPackageRepository,
)
from src.adapters.driven.persistence.application_data.route_repository import (
    ApplicationDataRouteRepository,
)
from src.application.services.customer_service import CustomerService
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Role
from src.domain.enums.item_status import ItemStatus


def make_create_route_uc(app: ApplicationData) -> CreateRouteUseCase:
    route_repo = ApplicationDataRouteRepository(app)
    return CreateRouteUseCase(route_repo)


def make_assign_truck_uc(app: ApplicationData) -> AssignTruckToRouteUseCase:
    route_repo = ApplicationDataRouteRepository(app)
    return AssignTruckToRouteUseCase(route_repo, app.vehicle_manager)


def make_create_package_uc(app: ApplicationData) -> CreatePackageUseCase:
    customer_repo = ApplicationDataCustomerRepository(app)
    package_repo = ApplicationDataPackageRepository(app)
    customer_service = CustomerService(customer_repo)
    return CreatePackageUseCase(customer_service, package_repo)


def _allow_all(*_args: Any, **_kwargs: Any) -> bool:
    return True


def _mk_app() -> Any:
    """ApplicationData with permissive authz and a stubbed vehicle manager."""
    app = ApplicationData(current_user=None)
    app.authz = SimpleNamespace(  # type: ignore[assignment]
        has=_allow_all,
        has_all=_allow_all,
    )
    app.vehicle_manager = MagicMock()  # type: ignore[assignment]
    app.vehicle_manager.vehicles = []
    return app


class _FakeCustomer:
    def __init__(
        self,
        customer_id: int = 1,
        name: str = "Name",
        email: str = "",
        phone_number: str = "",
    ) -> None:
        self.customer_id = customer_id
        self.name = name
        self.email = email
        self.phone_number = phone_number
        self.packages: list[Any] = []

    def add_package(self, pkg: Any) -> None:
        old_customer = getattr(pkg, "customer", None)
        if (
            old_customer is not None
            and old_customer is not self
            and hasattr(old_customer, "_remove_package_link")
        ):
            old_customer._remove_package_link(pkg)
        self._add_package_link(pkg)

    def _add_package_link(self, pkg: Any) -> None:
        if pkg not in self.packages:
            self.packages.append(pkg)
        pkg.customer = self

    def _remove_package_link(self, pkg: Any) -> None:
        if pkg in self.packages:
            self.packages.remove(pkg)
        if getattr(pkg, "customer", None) is self:
            pkg.customer = None


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
        if pkg not in self.packages:
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
        self,
        package_id: int,
        start: str,
        end: str,
        weight: float = 1.0,
        customer: Any = None,
    ) -> None:
        self.package_id = package_id
        self.start_location = start
        self.end_location = end
        self.weight = weight
        self.customer: Any = customer or _FakeCustomer()
        self.route: Any = None
        self.status: str | None = None

    def _set_package_id(self, package_id: int) -> None:
        self.package_id = package_id


def _make_contact_info(name: str, email: str, phone_number: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        email=email,
        phone_number=phone_number,
    )


def _make_fake_customer(customer_id: int, contact: Any) -> _FakeCustomer:
    return _FakeCustomer(
        customer_id=customer_id,
        name=getattr(contact, "name", "Name"),
        email=getattr(contact, "email", ""),
        phone_number=getattr(contact, "phone_number", ""),
    )


def _make_fake_package(*args: Any, **kwargs: Any) -> _FakePackage:
    customer = kwargs.get("customer")
    if customer is None and args:
        customer = args[-1]
    return _FakePackage(
        package_id=1,
        start="SYD",
        end="MEL",
        weight=1.0,
        customer=customer,
    )


def _make_fake_route(*args: Any, **kwargs: Any) -> _FakeRoute:
    route_id = kwargs.get("route_id", 10)
    locations = list(args) if args else ["SYD", "MEL"]
    departure_time = kwargs.get("departure_time")
    return _FakeRoute(route_id=route_id, locations=locations, departure_time=departure_time)


class ApplicationData_Heartbeat_Should(unittest.TestCase):
    def test_heartbeat_moves_trucks_and_updates_packages(self) -> None:
        app = _mk_app()
        base = datetime(2025, 1, 1, 8, 0)

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

        r2 = _FakeRoute(
            2,
            ["S2", "E2"],
            departure_time=base,
            eta_final=base + timedelta(hours=1),
        )
        t2 = _FakeTruck(vehicle_id=2)
        r2.truck = t2
        t2.route = r2

        r3 = _FakeRoute(
            3,
            ["S3", "M3", "E3"],
            departure_time=base,
            eta_final=base + timedelta(hours=2),
        )
        t3 = _FakeTruck(vehicle_id=3)
        r3.truck = t3
        t3.route = r3

        r4 = _FakeRoute(4, ["S4", "E4"], departure_time=None, eta_final=None)

        p_a = _FakePackage(1, "S3", "M3", weight=1, customer=_FakeCustomer(customer_id=1))
        p_b = _FakePackage(2, "S3", "E3", weight=1, customer=_FakeCustomer(customer_id=1))
        r3.assign_package(p_a)
        r3.assign_package(p_b)

        app._routes = [r1, r2, r3, r4]
        app.vehicle_manager.vehicles = [t1, t2, t3]
        app._packages += [p_a, p_b]

        summary1 = app.heartbeat(now=base)
        self.assertGreaterEqual(summary1["trucks_moved"], 0)

        mid = base + timedelta(minutes=30)
        summary2 = app.heartbeat(now=mid)
        self.assertGreaterEqual(summary2["trucks_moved"], 1)
        self.assertEqual(p_a.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(p_b.status, ItemStatus.IN_PROGRESS)

        summary3 = app.heartbeat(now=base + timedelta(hours=2))
        self.assertGreaterEqual(summary3["trucks_released"], 1)

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
            CI.side_effect = _make_contact_info
            Cust.side_effect = _make_fake_customer
            DP.side_effect = _make_fake_package
            DR.side_effect = _make_fake_route

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
            makedirs.assert_called_once()
            replace.assert_called_once()

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

        route.assign_package(pkg)
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

    def test_apply_invalid_payload_preserves_existing_state(self) -> None:
        app = ApplicationData(current_user=None)
        create_route = make_create_route_uc(app)
        assign_truck = make_assign_truck_uc(app)

        route = create_route.execute(["SYD", "MEL"], departure_time=None)
        truck = app.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.current_location = "SYD"
        assign_truck.execute(1001, route.route_id, now=datetime(2027, 1, 1, 10, 0))

        bad_payload = {
            "schema_version": 1,
            "counters": {"next_customer_id": 1, "next_package_id": 1, "next_route_id": 1},
            "customers": [],
            "packages": [
                {
                    "package_id": 1,
                    "start": "SYD",
                    "end": "MEL",
                    "weight": 1.0,
                    "customer_id": 999,
                    "route_id": None,
                }
            ],
            "routes": [],
        }

        with self.assertRaises(ValueError):
            app._apply_state(bad_payload) # pyright: ignore[reportPrivateUsage]

        self.assertEqual(app.route_store, [route])
        self.assertIs(truck.route, route)
        route_repo = ApplicationDataRouteRepository(app)
        self.assertIs(route_repo.get_by_id(route.route_id), route)

    def test_apply_state_resets_existing_truck_assignments_before_loading(self) -> None:
        app = ApplicationData(current_user=None)
        create_route = make_create_route_uc(app)
        assign_truck = make_assign_truck_uc(app)

        route = create_route.execute(["SYD", "MEL"], departure_time=None)
        truck = app.vehicle_manager.find_by_id(1001)
        assert truck is not None
        truck.current_location = "SYD"
        assign_truck.execute(1001, route.route_id, now=datetime(2027, 1, 1, 10, 0))

        empty_payload: dict[str, Any] = {
            "schema_version": 1,
            "counters": {"next_customer_id": 1, "next_package_id": 1, "next_route_id": 1},
            "customers": [],
            "packages": [],
            "routes": [],
        }

        app._apply_state(empty_payload) # pyright: ignore[reportPrivateUsage]

        self.assertEqual(app.route_store, [])
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, "Free")

    def test_apply_state_rejects_duplicate_customer_contacts(self) -> None:
        app = ApplicationData(current_user=None)
        payload = {
            "schema_version": 1,
            "counters": {"next_customer_id": 3, "next_package_id": 1, "next_route_id": 1},
            "customers": [
                {"customer_id": 1, "name": "Alice", "email": "dup@example.com", "phone": "0412345678"},
                {"customer_id": 2, "name": "Bob", "email": "dup@example.com", "phone": "0499999999"},
            ],
            "packages": [],
            "routes": [],
        }

        with self.assertRaises(ValueError) as ctx:
            app._apply_state(payload) # pyright: ignore[reportPrivateUsage]

        self.assertIn("Email already in use", str(ctx.exception))


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

    def test_employee_cannot_view_all_customers(self) -> None:
        app = self._app_for_role(Role.EMPLOYEE)
        with self.assertRaises(PermissionError):
            app.view_all_customers()

    def test_manager_can_save_state(self) -> None:
        app = self._app_for_role(Role.MANAGER)
        with patch.object(app, "_persist_to_file", return_value="/fake/path"):
            result = app.save("state.json")
            self.assertIn("/fake/path", result)

