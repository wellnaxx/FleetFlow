import unittest
from unittest.mock import MagicMock

from src.application.use_cases.routes.view_route import ViewRouteUseCase


class ViewRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = ViewRouteUseCase(self.mock_routes)

    def test_returns_route_when_found(self) -> None:
        route = MagicMock()
        route.route_id = 12
        self.mock_routes.get_by_id.return_value = route

        result = self.use_case.execute(12)

        self.assertIs(result, route)
        self.mock_routes.get_by_id.assert_called_once_with(12)

    def test_raises_when_route_not_found(self) -> None:
        self.mock_routes.get_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(77)

        self.assertIn("Route with ID 77 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(77)
