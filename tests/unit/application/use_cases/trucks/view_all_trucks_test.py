import unittest
from unittest.mock import MagicMock

from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewAllTrucksUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_vehicles = MagicMock()
        self.use_case = ViewAllTrucksUseCase(self.mock_vehicles, manager_authz())

    def test_returns_all_trucks_from_vehicle_manager(self) -> None:
        trucks = [MagicMock(), MagicMock()]
        self.mock_vehicles.list_fleet.return_value = trucks

        result = self.use_case.execute()

        self.assertEqual(result, trucks)
        self.mock_vehicles.list_fleet.assert_called_once_with()

    def test_returns_empty_list_when_no_trucks_exist(self) -> None:
        self.mock_vehicles.list_fleet.return_value = []

        result = self.use_case.execute()

        self.assertEqual(result, [])
        self.mock_vehicles.list_fleet.assert_called_once_with()
