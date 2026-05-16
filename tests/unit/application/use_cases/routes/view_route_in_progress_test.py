import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewRoutesInProgressUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = ViewRoutesInProgressUseCase(self.mock_routes, manager_authz())

    def test_returns_only_in_progress_routes(self) -> None:
        now = datetime(2025, 9, 27, 12, 0)

        route1 = MagicMock()
        route1.current_position.return_value = SimpleNamespace(kind="AT_STOP")

        route2 = MagicMock()
        route2.current_position.return_value = SimpleNamespace(kind="IN_TRANSIT")

        route3 = MagicMock()
        route3.current_position.return_value = SimpleNamespace(kind="BEFORE_START")

        route4 = MagicMock()
        route4.current_position.return_value = SimpleNamespace(kind="AFTER_END")

        self.mock_routes.list_all.return_value = [route1, route2, route3, route4]

        result = self.use_case.execute(now=now)

        self.assertEqual(
            result,
            [
                (route1, route1.current_position.return_value),
                (route2, route2.current_position.return_value),
            ],
        )
        self.mock_routes.list_all.assert_called_once_with()
        route1.current_position.assert_called_once_with(now)
        route2.current_position.assert_called_once_with(now)
        route3.current_position.assert_called_once_with(now)
        route4.current_position.assert_called_once_with(now)

    def test_returns_empty_list_when_no_routes_in_progress(self) -> None:
        now = datetime(2025, 9, 27, 12, 0)

        route1 = MagicMock()
        route1.current_position.return_value = SimpleNamespace(kind="BEFORE_START")

        route2 = MagicMock()
        route2.current_position.return_value = SimpleNamespace(kind="AFTER_END")

        self.mock_routes.list_all.return_value = [route1, route2]

        result = self.use_case.execute(now=now)

        self.assertEqual(result, [])
        self.mock_routes.list_all.assert_called_once_with()
        route1.current_position.assert_called_once_with(now)
        route2.current_position.assert_called_once_with(now)

    def test_returns_empty_list_when_no_routes_exist(self) -> None:
        now = datetime(2025, 9, 27, 12, 0)
        self.mock_routes.list_all.return_value = []

        result = self.use_case.execute(now=now)

        self.assertEqual(result, [])
        self.mock_routes.list_all.assert_called_once_with()
