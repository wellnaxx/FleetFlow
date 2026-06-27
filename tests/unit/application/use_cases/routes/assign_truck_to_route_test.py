import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.exceptions.application_errors import ConflictError, NotFoundError
from src.application.use_cases.routes.assign_truck_to_route import (
    AssignTruckToRouteUseCase,
)
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus
from tests.unit.application.use_cases.authz_helpers import manager_authz


class AssignTruckToRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.mock_vehicles = MagicMock()
        self.mock_uow_routes = MagicMock()
        self.mock_uow_trucks = MagicMock()
        self.mock_unit_of_work = MagicMock()
        self.mock_unit_of_work.__enter__.return_value = self.mock_unit_of_work
        self.mock_unit_of_work.routes = self.mock_uow_routes
        self.mock_unit_of_work.trucks = self.mock_uow_trucks
        self.use_case = AssignTruckToRouteUseCase(
            self.mock_routes, self.mock_vehicles, self.mock_unit_of_work, manager_authz()
        )

    def test_raises_when_route_not_found(self) -> None:
        self.mock_routes.get_by_id.return_value = None

        with self.assertRaises(NotFoundError) as ctx:
            self.use_case.execute(11, 22, now=datetime(2025, 10, 12, 6, 0))

        self.assertIn("Route with ID 22 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(22)
        self.mock_vehicles.find_by_id.assert_not_called()
        self.mock_uow_routes.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_not_called()
        self.mock_unit_of_work.__enter__.assert_not_called()
        self.mock_unit_of_work.commit.assert_not_called()

    def test_raises_when_truck_not_found(self) -> None:
        route = SimpleNamespace(route_id=22, departure_time=None, start_location="SYD", truck=None)
        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = None

        with self.assertRaises(NotFoundError) as ctx:
            self.use_case.execute(11, 22, now=datetime(2025, 10, 12, 6, 0))

        self.assertIn("Truck with ID 11 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(22)
        self.mock_vehicles.find_by_id.assert_called_once_with(11)
        self.mock_uow_routes.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_not_called()
        self.mock_unit_of_work.__enter__.assert_not_called()
        self.mock_unit_of_work.commit.assert_not_called()

    def test_schedules_route_when_unscheduled(self) -> None:
        fixed_now = datetime(2025, 10, 12, 6, 0)

        route = SimpleNamespace(
            route_id=22,
            departure_time=None,
            start_location="SYD",
            truck=None,
            total_distance_km=100,
        )
        route.total_assigned_weight = MagicMock(return_value=0.0)
        route.maximum_segment_load = MagicMock(return_value=0.0)

        def _set_departure(when: datetime, *, occurred_at: datetime) -> None:
            self.assertEqual(occurred_at, fixed_now)
            route.departure_time = when

        route.schedule = MagicMock(side_effect=_set_departure)
        route.snapshot_state = MagicMock(return_value=object())
        route.restore_state = MagicMock()
        route.event_checkpoint = MagicMock(return_value=0)
        route.restore_event_checkpoint = MagicMock()

        truck = MagicMock()
        truck.vehicle_id = 11
        route.assign_truck = MagicMock(
            side_effect=lambda assigned_truck, *, occurred_at: setattr(route, "truck", assigned_truck) # pyright: ignore[reportUnknownLambdaType]
        )

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = truck
        self.mock_vehicles.is_suitable_for_route.return_value = (True, "")

        result = self.use_case.execute(11, 22, now=fixed_now)

        self.assertEqual(result.route_id, 22)
        self.assertEqual(result.truck_id, 11)
        self.assertIs(result.route, route)
        self.assertEqual(self.mock_vehicles.is_suitable_for_route.call_args.args[1].departure_time, fixed_now)
        route.schedule.assert_called_once_with(fixed_now, occurred_at=fixed_now)
        route.assign_truck.assert_called_once_with(truck, occurred_at=fixed_now)
        self.assertIs(route.truck, truck)
        self.mock_routes.update_state.assert_not_called()
        self.mock_uow_routes.update_state.assert_called_once_with(route)
        self.mock_uow_trucks.update_state.assert_called_once_with(truck)
        self.mock_unit_of_work.commit.assert_called_once_with()

    def test_does_not_reschedule_when_route_already_scheduled(self) -> None:
        fixed_now = datetime(2025, 10, 12, 6, 0)

        route = SimpleNamespace(
            route_id=22,
            departure_time=datetime(2025, 10, 13, 6, 0),
            start_location="SYD",
            truck=None,
        )
        route.total_assigned_weight = MagicMock(return_value=0.0)
        route.maximum_segment_load = MagicMock(return_value=0.0)
        route.schedule = MagicMock()
        route.snapshot_state = MagicMock(return_value=object())
        route.restore_state = MagicMock()
        route.event_checkpoint = MagicMock(return_value=0)
        route.restore_event_checkpoint = MagicMock()

        truck = MagicMock()
        truck.vehicle_id = 11
        route.assign_truck = MagicMock(
            side_effect=lambda assigned_truck, *, occurred_at: setattr(route, "truck", assigned_truck) # pyright: ignore[reportUnknownLambdaType]
        )

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = truck
        self.mock_vehicles.is_suitable_for_route.return_value = (True, "")

        result = self.use_case.execute(11, 22, now=fixed_now)

        self.assertEqual(result.route_id, 22)
        self.assertEqual(result.truck_id, 11)
        self.assertIs(result.route, route)
        route.schedule.assert_not_called()
        self.mock_vehicles.is_suitable_for_route.assert_called_once_with(truck, route)
        route.assign_truck.assert_called_once_with(truck, occurred_at=fixed_now)
        self.assertIs(route.truck, truck)
        self.mock_routes.update_state.assert_not_called()
        self.mock_uow_routes.update_state.assert_called_once_with(route)
        self.mock_uow_trucks.update_state.assert_called_once_with(truck)
        self.mock_unit_of_work.commit.assert_called_once_with()

    def test_raises_when_truck_is_not_suitable(self) -> None:
        fixed_now = datetime(2025, 10, 12, 6, 0)

        route = SimpleNamespace(
            route_id=22,
            departure_time=None,
            start_location="SYD",
            truck=None,
            total_distance_km=100,
        )
        route.total_assigned_weight = MagicMock(return_value=0.0)
        route.maximum_segment_load = MagicMock(return_value=0.0)

        def _set_departure(when: datetime) -> None:
            route.departure_time = when

        route.schedule = MagicMock(side_effect=_set_departure)

        truck = MagicMock()
        truck.vehicle_id = 11

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = truck
        self.mock_vehicles.is_suitable_for_route.return_value = (False, "range too short")

        with self.assertRaises(ConflictError) as ctx:
            self.use_case.execute(11, 22, now=fixed_now)

        self.assertIn("Truck 11 is not suitable for route 22: range too short", str(ctx.exception))
        route.schedule.assert_not_called()
        truck.assign.assert_not_called()
        self.assertIsNone(route.truck)
        self.assertIsNone(route.departure_time)
        self.mock_uow_routes.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_not_called()
        self.mock_unit_of_work.__enter__.assert_not_called()
        self.mock_unit_of_work.commit.assert_not_called()

    def test_assigns_truck_to_route_on_success(self) -> None:
        fixed_now = datetime(2025, 10, 12, 6, 0)

        route = SimpleNamespace(
            route_id=22,
            departure_time=datetime(2025, 10, 13, 6, 0),
            start_location="SYD",
            truck=None,
        )
        route.total_assigned_weight = MagicMock(return_value=0.0)
        route.schedule = MagicMock()
        route.snapshot_state = MagicMock(return_value=object())
        route.restore_state = MagicMock()
        route.event_checkpoint = MagicMock(return_value=0)
        route.restore_event_checkpoint = MagicMock()

        truck = MagicMock()
        truck.vehicle_id = 11
        route.assign_truck = MagicMock(
            side_effect=lambda assigned_truck, *, occurred_at: setattr(route, "truck", assigned_truck) # pyright: ignore[reportUnknownLambdaType]
        )

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = truck
        self.mock_vehicles.is_suitable_for_route.return_value = (True, "")

        result = self.use_case.execute(11, 22, now=fixed_now)

        self.assertEqual(result.route_id, 22)
        self.assertEqual(result.truck_id, 11)
        self.assertIs(result.route, route)
        route.assign_truck.assert_called_once_with(truck, occurred_at=fixed_now)
        self.assertIs(route.truck, truck)
        self.mock_routes.update_state.assert_not_called()
        self.mock_uow_routes.update_state.assert_called_once_with(route)
        self.mock_uow_trucks.update_state.assert_called_once_with(truck)
        self.mock_unit_of_work.commit.assert_called_once_with()

    def test_restores_route_and_truck_state_when_persistence_fails(self) -> None:
        fixed_now = datetime(2025, 10, 12, 6, 0)
        route = DeliveryRoute("SYD", "MEL", route_id=22)
        truck = Truck(11, TruckModel.SCANIA, 42000, 8000)
        error = RuntimeError("write failed")

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = truck
        self.mock_vehicles.is_suitable_for_route.return_value = (True, "")
        self.mock_uow_routes.update_state.side_effect = error

        with self.assertRaises(RuntimeError) as ctx:
            self.use_case.execute(11, 22, now=fixed_now)

        self.assertIs(ctx.exception, error)
        self.assertIsNone(route.departure_time)
        self.assertEqual(route.status, RouteStatus.PLANNED)
        self.assertIsNone(route.truck)
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertIsNone(truck.busy_from)
        self.assertIsNone(truck.busy_until)
        self.assertEqual(route.pending_events, ())

    def test_raises_when_route_already_has_a_truck(self) -> None:
        route = SimpleNamespace(
            route_id=22,
            departure_time=datetime(2025, 10, 13, 6, 0),
            start_location="SYD",
            truck=SimpleNamespace(vehicle_id=7),
        )
        route.total_assigned_weight = MagicMock(return_value=0.0)
        route.schedule = MagicMock()
        self.mock_routes.get_by_id.return_value = route

        with self.assertRaises(ConflictError) as ctx:
            self.use_case.execute(11, 22, now=datetime(2025, 10, 12, 6, 0))

        self.assertIn("Route 22 already has truck 7 assigned", str(ctx.exception))
        self.mock_vehicles.find_by_id.assert_called_once_with(11)
        self.mock_vehicles.is_suitable_for_route.assert_not_called()
        route.schedule.assert_not_called()
        self.mock_uow_routes.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_not_called()
        self.mock_unit_of_work.__enter__.assert_not_called()
        self.mock_unit_of_work.commit.assert_not_called()
