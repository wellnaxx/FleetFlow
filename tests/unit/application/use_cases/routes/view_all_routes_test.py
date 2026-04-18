import unittest
from unittest.mock import MagicMock

from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase


class ViewAllRoutesUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = ViewAllRoutesUseCase(self.mock_routes)

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
