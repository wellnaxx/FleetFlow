import unittest
from unittest.mock import MagicMock

from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class RemovePackageUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_packages = MagicMock()
        self.use_case = RemovePackageUseCase(self.mock_packages, manager_authz())

    def test_raises_when_package_not_found(self) -> None:
        self.mock_packages.get_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(42)

        self.assertIn("Package with ID 42 not found", str(ctx.exception))
        self.mock_packages.get_by_id.assert_called_once_with(42)
        self.mock_packages.remove.assert_not_called()

    def test_removes_package_without_route(self) -> None:
        package = MagicMock()
        package.package_id = 42
        package.route = None
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(42)

        self.assertIs(result, package)
        self.mock_packages.get_by_id.assert_called_once_with(42)
        package.customer.remove_package.assert_called_once_with(package)
        self.mock_packages.remove.assert_called_once_with(42)

    def test_detaches_from_route_before_removal(self) -> None:
        route = MagicMock()
        package = MagicMock()
        package.package_id = 42
        package.route = route
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(42)

        self.assertIs(result, package)
        self.mock_packages.get_by_id.assert_called_once_with(42)
        route.detach_package.assert_called_once_with(package)
        package.customer.remove_package.assert_called_once_with(package)
        self.mock_packages.remove.assert_called_once_with(42)

    def test_propagates_customer_unlink_error(self) -> None:
        package = MagicMock()
        package.package_id = 42
        package.route = None
        package.customer.remove_package.side_effect = ValueError("customer unlink failed")
        self.mock_packages.get_by_id.return_value = package

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(42)

        self.assertIn("customer unlink failed", str(ctx.exception))
        package.customer.remove_package.assert_called_once_with(package)
        self.mock_packages.remove.assert_not_called()

    def test_propagates_detach_error(self) -> None:
        route = MagicMock()
        route.detach_package.side_effect = ValueError("Package is not assigned to this route")

        package = MagicMock()
        package.package_id = 42
        package.route = route
        self.mock_packages.get_by_id.return_value = package

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(42)

        self.assertIn("Package is not assigned to this route", str(ctx.exception))
        route.detach_package.assert_called_once_with(package)
        package.customer.remove_package.assert_not_called()
        self.mock_packages.remove.assert_not_called()
