import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.use_cases.routes.find_suitable_routes_for_package import FindSuitableRoutesForPackageUseCase


class FindSuitableRoutesForPackageUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.mock_packages = MagicMock()
        self.use_case = FindSuitableRoutesForPackageUseCase(self.mock_routes, self.mock_packages)

    def test_raises_when_package_not_found(self) -> None:
        self.mock_packages.get_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(42)

        self.assertIn("Package with ID 42 not found.", str(ctx.exception))
        self.mock_packages.get_by_id.assert_called_once_with(42)
        self.mock_routes.list_all.assert_not_called()

    def test_returns_sorted_suitable_routes(self) -> None:
        package = SimpleNamespace(package_id=7, start_location="SYD", end_location="MEL", weight=2.0)

        route_with_eta = MagicMock()
        route_with_eta.can_accept_package.return_value = None
        route_with_eta.truck = SimpleNamespace(capacity=10.0)
        route_with_eta.total_assigned_weight.return_value = 4.0
        route_with_eta.arrival_time_at.return_value = datetime(2025, 1, 1, 10, 0)

        route_no_eta = MagicMock()
        route_no_eta.can_accept_package.return_value = None
        route_no_eta.truck = None
        route_no_eta.total_assigned_weight.return_value = 0.0
        route_no_eta.arrival_time_at.side_effect = ValueError("unscheduled")

        route_rejected = MagicMock()
        route_rejected.can_accept_package.return_value = "not suitable"

        self.mock_packages.get_by_id.return_value = package
        self.mock_routes.list_all.return_value = [route_no_eta, route_rejected, route_with_eta]

        result = self.use_case.execute(7)

        self.assertEqual([item.route for item in result], [route_with_eta, route_no_eta])
        self.assertEqual(result[0].eta, datetime(2025, 1, 1, 10, 0))
        self.assertEqual(result[0].capacity_left, 6.0)
        self.assertEqual(result[0].end_city, "MEL")
        self.assertIsNone(result[1].eta)
        self.assertIsNone(result[1].capacity_left)

        route_with_eta.can_accept_package.assert_called_once_with(package)
        route_no_eta.can_accept_package.assert_called_once_with(package)
        route_rejected.can_accept_package.assert_called_once_with(package)

    def test_returns_empty_list_when_no_routes_accept_package(self) -> None:
        package = SimpleNamespace(package_id=7, start_location="SYD", end_location="MEL", weight=2.0)
        route1 = MagicMock()
        route1.can_accept_package.return_value = "wrong order"
        route2 = MagicMock()
        route2.can_accept_package.return_value = "capacity exceeded"

        self.mock_packages.get_by_id.return_value = package
        self.mock_routes.list_all.return_value = [route1, route2]

        result = self.use_case.execute(7)

        self.assertEqual(result, [])
