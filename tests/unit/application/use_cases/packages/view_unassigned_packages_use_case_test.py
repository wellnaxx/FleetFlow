import unittest
from unittest.mock import MagicMock

from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase


class ViewUnassignedPackagesUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_packages = MagicMock()
        self.use_case = ViewUnassignedPackagesUseCase(self.mock_packages)

    def test_returns_unassigned_packages(self) -> None:
        package1 = MagicMock()
        package2 = MagicMock()
        self.mock_packages.list_unassigned.return_value = [package1, package2]

        result = self.use_case.execute()

        self.assertEqual(result, [package1, package2])
        self.mock_packages.list_unassigned.assert_called_once_with()

    def test_returns_empty_list_when_no_unassigned_packages(self) -> None:
        self.mock_packages.list_unassigned.return_value = []

        result = self.use_case.execute()

        self.assertEqual(result, [])
        self.mock_packages.list_unassigned.assert_called_once_with()
