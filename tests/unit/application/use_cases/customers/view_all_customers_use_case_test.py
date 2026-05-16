import unittest
from unittest.mock import MagicMock

from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewAllCustomersUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_customers = MagicMock()
        self.use_case = ViewAllCustomersUseCase(self.mock_customers, manager_authz())

    def test_returns_all_customers(self) -> None:
        c1 = MagicMock()
        c2 = MagicMock()
        self.mock_customers.list_all.return_value = [c1, c2]

        result = self.use_case.execute()

        self.assertEqual(result, [c1, c2])
        self.mock_customers.list_all.assert_called_once_with()

    def test_returns_empty_list_when_no_customers(self) -> None:
        self.mock_customers.list_all.return_value = []

        result = self.use_case.execute()

        self.assertEqual(result, [])
        self.mock_customers.list_all.assert_called_once_with()
