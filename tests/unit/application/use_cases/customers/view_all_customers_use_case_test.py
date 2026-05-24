import unittest
from unittest.mock import MagicMock

from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.application.use_cases.pagination import PageQuery
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

        self.assertEqual(result.items, (c1, c2))
        self.assertIsInstance(result.items, tuple)
        self.assertIsNone(result.total)
        self.assertIsNone(result.limit)
        self.assertEqual(result.offset, 0)
        self.assertEqual(result.count, 2)
        self.mock_customers.list_all.assert_called_once_with()

    def test_returns_empty_page_when_no_customers(self) -> None:
        self.mock_customers.list_all.return_value = []

        result = self.use_case.execute()

        self.assertEqual(result.items, ())
        self.assertEqual(result.count, 0)
        self.mock_customers.list_all.assert_called_once_with()

    def test_returns_paginated_customers(self) -> None:
        c1 = MagicMock()
        c2 = MagicMock()
        self.mock_customers.list_page.return_value = [c1, c2]

        result = self.use_case.execute(PageQuery(limit=2, offset=4))

        self.assertEqual(result.items, (c1, c2))
        self.assertIsNone(result.total)
        self.assertEqual(result.limit, 2)
        self.assertEqual(result.offset, 4)
        self.assertEqual(result.count, 2)
        self.mock_customers.list_page.assert_called_once_with(limit=2, offset=4)
        self.mock_customers.list_all.assert_not_called()

    def test_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(PageQuery(limit=0, offset=0))

        self.assertIn("Limit", str(ctx.exception))
        self.mock_customers.list_page.assert_not_called()

    def test_rejects_invalid_offset(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(PageQuery(limit=1, offset=-1))

        self.assertIn("Offset", str(ctx.exception))
        self.mock_customers.list_page.assert_not_called()

    def test_returns_paginated_customers_with_total(self) -> None:
        customer = MagicMock()
        self.mock_customers.list_page_with_total.return_value = ([customer], 7)

        result = self.use_case.execute(PageQuery(limit=2, offset=4, include_total=True))

        self.assertEqual(result.items, (customer,))
        self.assertEqual(result.total, 7)
        self.assertEqual(result.count, 1)
        self.mock_customers.list_page_with_total.assert_called_once_with(limit=2, offset=4)

    def test_rejects_offset_without_limit(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(PageQuery(offset=1))

        self.assertIn("Offset", str(ctx.exception))
        self.mock_customers.list_all.assert_not_called()

    def test_requires_customer_view_permission(self) -> None:
        use_case = ViewAllCustomersUseCase(self.mock_customers, AuthorizationService(None))

        with self.assertRaises(PermissionError):
            use_case.execute()

        self.mock_customers.list_all.assert_not_called()
