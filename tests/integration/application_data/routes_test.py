import unittest
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from src.adapters.driven.persistence.application_data.route_repository import (
    ApplicationDataRouteRepository,
)
from src.application.use_cases.routes.assign_truck_to_route import (
    AssignTruckToRouteUseCase,
)
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.core.application_data import ApplicationData


def _allow_all(*_args: Any, **_kwargs: Any) -> bool:
    return True


def _mk_app() -> Any:
    app = ApplicationData(current_user=None)
    app.authz = MagicMock()  # type: ignore[assignment]
    app.authz.has.side_effect = _allow_all
    app.authz.has_all.side_effect = _allow_all
    app.vehicle_manager = MagicMock()  # type: ignore[assignment]
    app.vehicle_manager.vehicles = []
    return app


def make_create_route_uc(app: ApplicationData) -> CreateRouteUseCase:
    route_repo = ApplicationDataRouteRepository(app)
    return CreateRouteUseCase(route_repo)


def make_remove_route_uc(app: ApplicationData) -> RemoveRouteUseCase:
    route_repo = ApplicationDataRouteRepository(app)
    return RemoveRouteUseCase(route_repo)


def make_assign_truck_to_route_uc(app: ApplicationData) -> AssignTruckToRouteUseCase:
    route_repo = ApplicationDataRouteRepository(app)
    return AssignTruckToRouteUseCase(route_repo, app.vehicle_manager)


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
    def __init__(self, route_id: int, locations: list[str], departure_time: datetime | None = None) -> None:
        self.route_id = route_id
        self.locations = list(locations)
        self.start_location = locations[0]
        self.end_location = locations[-1]
        self.departure_time = departure_time
        self.truck: Any = None
        self.packages: list[Any] = []

    def schedule(self, when: datetime) -> None:
        self.departure_time = when

    def total_assigned_weight(self) -> float:
        return sum(getattr(p, "weight", 0.0) for p in self.packages)


class ApplicationDataBackedRoutesIntegration_Should(unittest.TestCase):
    def test_create_and_remove_route_updates_shared_state(self) -> None:
        app = _mk_app()
        create_route = make_create_route_uc(app)
        remove_route = make_remove_route_uc(app)

        route = create_route.execute(["SYD", "MEL"], None)
        self.assertIs(app.find_route(route.route_id), route)

        truck = _FakeTruck(vehicle_id=5)
        route.truck = truck  # type: ignore[assignment]
        truck.route = route

        removed = remove_route.execute(route.route_id)

        self.assertIs(removed, route)
        self.assertIsNone(app.find_route(route.route_id))
        self.assertIsNone(truck.route)

    def test_assign_truck_schedules_if_unscheduled_and_checks_suitability(self) -> None:
        app = _mk_app()
        route = _FakeRoute(1, ["S", "E"])
        app._routes = [route]

        truck = _FakeTruck(vehicle_id=5, capacity=10.0)
        app.vehicle_manager.find_by_id.return_value = truck
        app.vehicle_manager.is_suitable_for_route.return_value = (True, "")

        assign_truck = make_assign_truck_to_route_uc(app)
        now = datetime(2025, 1, 1, 10, 0)

        result = assign_truck.execute(5, 1, now=now)

        self.assertIs(result, route)
        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(route.departure_time, now)
        app.vehicle_manager.find_by_id.assert_called_once_with(5)
        app.vehicle_manager.is_suitable_for_route.assert_called_once_with(truck, route)

    def test_assign_truck_route_not_found_raises(self) -> None:
        app = _mk_app()
        assign_truck = make_assign_truck_to_route_uc(app)

        with self.assertRaises(ValueError) as ctx:
            assign_truck.execute(5, 999, now=datetime(2025, 1, 1, 10, 0))

        self.assertIn("Route with ID 999 not found", str(ctx.exception))
        app.vehicle_manager.find_by_id.assert_not_called()

    def test_assign_truck_truck_not_found_raises(self) -> None:
        app = _mk_app()
        route = _FakeRoute(1, ["S", "E"])
        app._routes = [route]
        app.vehicle_manager.find_by_id.return_value = None

        assign_truck = make_assign_truck_to_route_uc(app)

        with self.assertRaises(ValueError) as ctx:
            assign_truck.execute(99, 1, now=datetime(2025, 1, 1, 10, 0))

        self.assertIn("Truck with ID 99 not found", str(ctx.exception))

    def test_assign_truck_unsuitable_raises_and_does_not_link(self) -> None:
        app = _mk_app()
        route = _FakeRoute(1, ["S", "E"])
        app._routes = [route]

        truck = _FakeTruck(vehicle_id=5, capacity=10.0)
        app.vehicle_manager.find_by_id.return_value = truck
        app.vehicle_manager.is_suitable_for_route.return_value = (False, "range too short")

        assign_truck = make_assign_truck_to_route_uc(app)

        with self.assertRaises(ValueError) as ctx:
            assign_truck.execute(5, 1, now=datetime(2025, 1, 1, 10, 0))

        self.assertIn("Truck 5 is not suitable for route 1: range too short", str(ctx.exception))
        self.assertIsNone(route.truck)
        self.assertIsNone(truck.route)
