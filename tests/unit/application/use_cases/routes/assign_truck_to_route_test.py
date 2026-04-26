import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.use_cases.routes.assign_truck_to_route import (
    AssignTruckToRouteResult,
    AssignTruckToRouteUseCase,
)


class AssignTruckToRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.mock_vehicles = MagicMock()
        self.use_case = AssignTruckToRouteUseCase(self.mock_routes, self.mock_vehicles)

    def test_raises_when_route_not_found(self) -> None:
        self.mock_routes.get_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(11, 22, now=datetime(2025, 10, 12, 6, 0))

        self.assertIn("Route with ID 22 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(22)
        self.mock_vehicles.find_by_id.assert_not_called()

    def test_raises_when_truck_not_found(self) -> None:
        route = SimpleNamespace(route_id=22, departure_time=None, start_location="SYD", truck=None)
        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(11, 22, now=datetime(2025, 10, 12, 6, 0))

        self.assertIn("Truck with ID 11 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(22)
        self.mock_vehicles.find_by_id.assert_called_once_with(11)

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

        def _set_departure(when: datetime) -> None:
            route.departure_time = when

        route.schedule = MagicMock(side_effect=_set_departure)

        truck = MagicMock()
        truck.vehicle_id = 11

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = truck
        self.mock_vehicles.is_suitable_for_route.return_value = (True, "")

        result = self.use_case.execute(11, 22, now=fixed_now)

        self.assertEqual(result, AssignTruckToRouteResult(route_id=22, truck_id=11))
        self.assertEqual(self.mock_vehicles.is_suitable_for_route.call_args.args[1].departure_time, fixed_now)
        route.schedule.assert_called_once_with(fixed_now)
        self.assertIs(route.truck, truck)
        truck.assign.assert_called_once_with(route)

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

        truck = MagicMock()
        truck.vehicle_id = 11

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = truck
        self.mock_vehicles.is_suitable_for_route.return_value = (True, "")

        result = self.use_case.execute(11, 22, now=fixed_now)

        self.assertEqual(result, AssignTruckToRouteResult(route_id=22, truck_id=11))
        route.schedule.assert_not_called()
        self.mock_vehicles.is_suitable_for_route.assert_called_once_with(truck, route)
        self.assertIs(route.truck, truck)
        truck.assign.assert_called_once_with(route)

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

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(11, 22, now=fixed_now)

        self.assertIn("Truck 11 is not suitable for route 22: range too short", str(ctx.exception))
        route.schedule.assert_not_called()
        truck.assign.assert_not_called()
        self.assertIsNone(route.truck)
        self.assertIsNone(route.departure_time)

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

        truck = MagicMock()
        truck.vehicle_id = 11

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_by_id.return_value = truck
        self.mock_vehicles.is_suitable_for_route.return_value = (True, "")

        result = self.use_case.execute(11, 22, now=fixed_now)

        self.assertEqual(result, AssignTruckToRouteResult(route_id=22, truck_id=11))
        self.assertIs(route.truck, truck)
        truck.assign.assert_called_once_with(route)

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

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(11, 22, now=datetime(2025, 10, 12, 6, 0))

        self.assertIn("Route 22 already has truck 7 assigned", str(ctx.exception))
        self.mock_vehicles.find_by_id.assert_called_once_with(11)
        self.mock_vehicles.is_suitable_for_route.assert_not_called()
        route.schedule.assert_not_called()
