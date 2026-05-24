import unittest
from unittest.mock import MagicMock

from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewAllRoutesUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = ViewAllRoutesUseCase(self.mock_routes, manager_authz())

    def test_returns_all_routes(self) -> None:
        r1 = MagicMock()
        r2 = MagicMock()
        self.mock_routes.list_all.return_value = [r1, r2]

        result = self.use_case.execute()

        self.assertEqual(result, [r1, r2])
        self.mock_routes.list_all.assert_called_once_with()

    def test_returns_empty_list_when_no_routes(self) -> None:
        self.mock_routes.list_all.return_value = []

        result = self.use_case.execute()

        self.assertEqual(result, [])
        self.mock_routes.list_all.assert_called_once_with()

    def test_returns_requested_route_page(self) -> None:
        route = MagicMock()
        self.mock_routes.list_page.return_value = [route]

        result = self.use_case.execute(limit=10, offset=20)

        self.assertEqual(result, [route])
        self.mock_routes.list_page.assert_called_once_with(limit=10, offset=20)
        self.mock_routes.list_all.assert_not_called()

    def test_rejects_invalid_pagination(self) -> None:
        with self.assertRaises(ValueError):
            self.use_case.execute(limit=0)

        with self.assertRaises(ValueError):
            self.use_case.execute(limit=1, offset=-1)

        with self.assertRaises(ValueError):
            self.use_case.execute(offset=1)

        self.mock_routes.list_page.assert_not_called()

    def test_returns_requested_route_page_with_count(self) -> None:
        route = MagicMock()
        self.mock_routes.list_page_with_total.return_value = ([route], 3)

        result = self.use_case.execute_with_count(limit=10, offset=20)

        self.assertEqual(result, ([route], 3))
        self.mock_routes.list_page_with_total.assert_called_once_with(limit=10, offset=20)

    def test_returns_route_count(self) -> None:
        self.mock_routes.count_all.return_value = 3

        result = self.use_case.count()

        self.assertEqual(result, 3)
        self.mock_routes.count_all.assert_called_once_with()
