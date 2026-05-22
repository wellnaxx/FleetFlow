import unittest
from unittest.mock import MagicMock

from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewUnassignedPackagesUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_packages = MagicMock()
        self.use_case = ViewUnassignedPackagesUseCase(self.mock_packages, manager_authz())

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

    def test_returns_requested_unassigned_package_page(self) -> None:
        package = MagicMock()
        self.mock_packages.list_unassigned_page.return_value = [package]

        result = self.use_case.execute(limit=10, offset=20)

        self.assertEqual(result, [package])
        self.mock_packages.list_unassigned_page.assert_called_once_with(limit=10, offset=20)
        self.mock_packages.list_unassigned.assert_not_called()

    def test_rejects_invalid_pagination(self) -> None:
        with self.assertRaises(ValueError):
            self.use_case.execute(limit=0)

        with self.assertRaises(ValueError):
            self.use_case.execute(limit=1, offset=-1)

        with self.assertRaises(ValueError):
            self.use_case.execute(offset=1)

        self.mock_packages.list_unassigned_page.assert_not_called()

    def test_returns_requested_unassigned_page_with_count(self) -> None:
        package = MagicMock()
        self.mock_packages.list_unassigned_page_with_total.return_value = ([package], 2)

        result = self.use_case.execute_with_count(limit=10, offset=20)

        self.assertEqual(result, ([package], 2))
        self.mock_packages.list_unassigned_page_with_total.assert_called_once_with(
            limit=10,
            offset=20,
        )

    def test_returns_unassigned_package_count(self) -> None:
        self.mock_packages.count_unassigned.return_value = 2

        result = self.use_case.count()

        self.assertEqual(result, 2)
        self.mock_packages.count_unassigned.assert_called_once_with()
