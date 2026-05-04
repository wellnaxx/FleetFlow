import unittest
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.application.use_cases.routes.assign_truck_to_route import (
    AssignTruckToRouteResult,
    AssignTruckToRouteUseCase,
)
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.domain.value_objects.location_code import LocationCode


class _FakeTruck:
    def __init__(
        self,
        vehicle_id: int = 1,
        capacity: float = 100.0,
        current_location: str | LocationCode = "BASE",
    ) -> None:
        self.vehicle_id = vehicle_id
        self.capacity = capacity
        self.current_location = LocationCode(current_location)
        self.in_transit_to: LocationCode | None = None
        self.route: Any = None

    def assign(self, route: Any) -> bool:
        self.route = route
        self.current_location = LocationCode(route.start_location)
        return True

    def release(self, now: datetime | None = None, force: bool = False) -> bool:
        released = self.route is not None
        self.route = None
        self.in_transit_to = None
        return released


class RuntimeRoutesIntegrationTests(unittest.TestCase):
    def test_create_and_remove_route_updates_shared_repo_state(self) -> None:
        route_repo = InMemoryRouteRepository()
        package_repo = MagicMock()
        truck_repo = MagicMock()
        create_route = CreateRouteUseCase(route_repo)
        remove_route = RemoveRouteUseCase(route_repo, package_repo, truck_repo)

        route = create_route.execute([LocationCode("SYD"), LocationCode("MEL")], None)
        self.assertIs(route_repo.get_by_id(route.route_id), route)

        removed = remove_route.execute(route.route_id)

        self.assertIs(removed, route)
        self.assertIsNone(route_repo.get_by_id(route.route_id))
        package_repo.update_state.assert_not_called()
        truck_repo.update_state.assert_not_called()

    def test_assign_truck_schedules_route_and_links_truck(self) -> None:
        route_repo = InMemoryRouteRepository()
        route = CreateRouteUseCase(route_repo).execute([LocationCode("SYD"), LocationCode("MEL")], None)

        truck = _FakeTruck(vehicle_id=5, capacity=10.0, current_location=LocationCode("SYD"))
        vehicles = MagicMock()
        vehicles.find_by_id.return_value = truck
        vehicles.is_suitable_for_route.return_value = (True, "")
        truck_repo = MagicMock()

        result = AssignTruckToRouteUseCase(route_repo, vehicles, truck_repo).execute(
            5,
            route.route_id,
            now=datetime(2025, 1, 1, 10, 0),
        )

        self.assertEqual(result, AssignTruckToRouteResult(route_id=route.route_id, truck_id=5))
        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(route.departure_time, datetime(2025, 1, 1, 10, 0))
        self.assertEqual(truck.current_location, LocationCode("SYD"))
