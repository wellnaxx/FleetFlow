import unittest
from unittest.mock import MagicMock

from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewAllPackagesUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_packages = MagicMock()
        self.use_case = ViewAllPackagesUseCase(self.mock_packages, manager_authz())

    def test_returns_all_packages(self) -> None:
        package1 = MagicMock()
        package2 = MagicMock()
        self.mock_packages.list_all.return_value = [package1, package2]

        result = self.use_case.execute()

        self.assertEqual(result, [package1, package2])
        self.mock_packages.list_all.assert_called_once_with()

    def test_returns_empty_list_when_no_packages(self) -> None:
        self.mock_packages.list_all.return_value = []

        result = self.use_case.execute()

        self.assertEqual(result, [])
        self.mock_packages.list_all.assert_called_once_with()
