import unittest
from unittest.mock import MagicMock

from src.application.use_cases.routes.remove_route import RemoveRouteUseCase


class RemoveRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = RemoveRouteUseCase(self.mock_routes)

    def test_raises_when_route_not_found(self) -> None:
        self.mock_routes.get_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(42)

        self.assertIn("Route with ID 42 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(42)
        self.mock_routes.remove.assert_not_called()

    def test_removes_route_without_truck(self) -> None:
        route = MagicMock()
        route.route_id = 42
        route.truck = None
        route.packages = []
        self.mock_routes.get_by_id.return_value = route

        result = self.use_case.execute(42)

        self.assertIs(result, route)
        self.mock_routes.get_by_id.assert_called_once_with(42)
        self.mock_routes.remove.assert_called_once_with(42)

    def test_releases_truck_before_removal(self) -> None:
        truck = MagicMock()
        route = MagicMock()
        route.route_id = 42
        route.truck = truck
        route.packages = []
        self.mock_routes.get_by_id.return_value = route

        result = self.use_case.execute(42)

        self.assertIs(result, route)
        truck.release.assert_called_once_with(force=True)
        self.mock_routes.remove.assert_called_once_with(42)

    def test_release_error_stops_removal(self) -> None:
        truck = MagicMock()
        truck.release.side_effect = RuntimeError("truck release failed")

        route = MagicMock()
        route.route_id = 42
        route.truck = truck
        route.packages = []
        self.mock_routes.get_by_id.return_value = route

        with self.assertRaises(RuntimeError) as ctx:
            self.use_case.execute(42)

        self.assertIn("truck release failed", str(ctx.exception))
        truck.release.assert_called_once_with(force=True)
        self.mock_routes.remove.assert_not_called()

    def test_detaches_assigned_packages_before_removal(self) -> None:
        package1 = MagicMock()
        package2 = MagicMock()
        route = MagicMock()
        route.route_id = 42
        route.truck = None
        route.packages = [package1, package2]
        self.mock_routes.get_by_id.return_value = route

        self.use_case.execute(42)

        route.detach_package.assert_any_call(package1)
        route.detach_package.assert_any_call(package2)
        self.assertEqual(route.detach_package.call_count, 2)
        self.mock_routes.remove.assert_called_once_with(42)

    def test_detach_error_stops_removal(self) -> None:
        package = MagicMock()
        route = MagicMock()
        route.route_id = 42
        route.truck = None
        route.packages = [package]
        route.detach_package.side_effect = ValueError("detach failed")
        self.mock_routes.get_by_id.return_value = route

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(42)

        self.assertIn("detach failed", str(ctx.exception))
        route.detach_package.assert_called_once_with(package)
        self.mock_routes.remove.assert_not_called()
