import unittest
from unittest.mock import MagicMock

from src.application.use_cases.packages.view_package import ViewPackageUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewPackageUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_packages = MagicMock()
        self.use_case = ViewPackageUseCase(self.mock_packages, manager_authz())

    def test_returns_package_when_found(self) -> None:
        package = MagicMock()
        package.package_id = 123
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(123)

        self.assertIs(result, package)
        self.mock_packages.get_by_id.assert_called_once_with(123)

    def test_raises_when_package_not_found(self) -> None:
        self.mock_packages.get_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(999)

        self.assertIn("Package with ID 999 not found", str(ctx.exception))
        self.mock_packages.get_by_id.assert_called_once_with(999)
