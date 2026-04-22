import unittest
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from src.adapters.driven.persistence.application_data.customer_repository import (
    ApplicationDataCustomerRepository,
)
from src.adapters.driven.persistence.application_data.package_repository import (
    ApplicationDataPackageRepository,
)
from src.adapters.driven.persistence.application_data.route_repository import (
    ApplicationDataRouteRepository,
)
from src.adapters.driven.persistence.json.serialization import dt_to_str
from src.application.services.customer_service import CustomerService
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Role


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

    def test_apply_state_does_not_run_derived_heartbeat_updates(self) -> None:
        payload = {
            "schema_version": 1,
            "counters": {"next_customer_id": 2, "next_package_id": 2, "next_route_id": 2},
            "customers": [
                {"customer_id": 1, "name": "Carl", "email": "carl@test.com", "phone": ""},
            ],
            "packages": [
                {
                    "package_id": 1,
                    "start": "SYD",
                    "end": "MEL",
                    "weight": 2.0,
                    "customer_id": 1,
                    "route_id": 1,
                }
            ],
            "routes": [
                {
                    "route_id": 1,
                    "locations": ["SYD", "MEL"],
                    "departure_time": dt_to_str(datetime(2027, 1, 1, 10, 0)),
                    "truck_vehicle_id": None,
                    "package_ids": [1],
                }
            ],
        }

        app = ApplicationData(current_user=None)
        app._apply_state(payload)

        self.assertEqual(len(app.package_store), 1)
        self.assertIsNone(app.route_store[0].status)
        self.assertIsNone(app.package_store[0].status)

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
        from src.application.services.authorization_service import AuthorizationService
        from src.domain.entities.users.employee import Employee
        from src.domain.entities.users.manager import Manager

        user = Employee("Test") if role == Role.EMPLOYEE else Manager("Test")
        app = ApplicationData(current_user=user)
        app.authz = AuthorizationService(user)
        return app

    def test_employee_cannot_view_all_customers(self) -> None:
        app = self._app_for_role(Role.EMPLOYEE)
        with self.assertRaises(PermissionError):
            app.view_all_customers()

