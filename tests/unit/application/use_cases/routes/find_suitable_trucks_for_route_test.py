import unittest
from unittest.mock import MagicMock

from src.application.use_cases.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class FindSuitableTrucksForRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.mock_vehicles = MagicMock()
        self.use_case = FindSuitableTrucksForRouteUseCase(self.mock_routes, self.mock_vehicles, manager_authz())

    def test_raises_when_route_not_found(self) -> None:
        self.mock_routes.get_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(15)

        self.assertIn("Route with ID 15 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(15)
        self.mock_vehicles.find_available_for_route.assert_not_called()

    def test_returns_available_trucks_for_route(self) -> None:
        route = MagicMock()
        trucks = [MagicMock(), MagicMock()]

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_available_for_route.return_value = trucks

        result = self.use_case.execute(15)

        self.assertEqual(result, trucks)
        self.mock_routes.get_by_id.assert_called_once_with(15)
        self.mock_vehicles.find_available_for_route.assert_called_once_with(route)

    def test_returns_empty_list_when_no_trucks_are_available(self) -> None:
        route = MagicMock()

        self.mock_routes.get_by_id.return_value = route
        self.mock_vehicles.find_available_for_route.return_value = []

        result = self.use_case.execute(15)

        self.assertEqual(result, [])
        self.mock_routes.get_by_id.assert_called_once_with(15)
        self.mock_vehicles.find_available_for_route.assert_called_once_with(route)
