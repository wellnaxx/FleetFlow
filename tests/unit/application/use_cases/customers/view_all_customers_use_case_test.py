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

    def test_returns_paginated_customers(self) -> None:
        c1 = MagicMock()
        c2 = MagicMock()
        self.mock_customers.list_page.return_value = [c1, c2]

        result = self.use_case.execute(limit=2, offset=4)

        self.assertEqual(result, [c1, c2])
        self.mock_customers.list_page.assert_called_once_with(limit=2, offset=4)
        self.mock_customers.list_all.assert_not_called()

    def test_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(limit=0, offset=0)

        self.assertIn("Limit", str(ctx.exception))
        self.mock_customers.list_page.assert_not_called()

    def test_rejects_invalid_offset(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(limit=1, offset=-1)

        self.assertIn("Offset", str(ctx.exception))
        self.mock_customers.list_page.assert_not_called()

    def test_returns_paginated_customers_with_count(self) -> None:
        customer = MagicMock()
        self.mock_customers.list_page_with_total.return_value = ([customer], 7)

        result = self.use_case.execute_with_count(limit=2, offset=4)

        self.assertEqual(result, ([customer], 7))
        self.mock_customers.list_page_with_total.assert_called_once_with(limit=2, offset=4)

    def test_counts_customers(self) -> None:
        self.mock_customers.count_all.return_value = 7

        result = self.use_case.count()

        self.assertEqual(result, 7)
        self.mock_customers.count_all.assert_called_once_with()
