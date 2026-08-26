import unittest
from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.queries.routes.view_routes_in_progress import ViewRoutesInProgressQuery
from src.application.services.authorization_service import AuthorizationService
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

        result = self.use_case.execute(ViewRoutesInProgressQuery(now=now))

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

        result = self.use_case.execute(ViewRoutesInProgressQuery(now=now))

        self.assertEqual(result, [])
        self.mock_routes.list_all.assert_called_once_with()
        route1.current_position.assert_called_once_with(now)
        route2.current_position.assert_called_once_with(now)

    def test_returns_empty_list_when_no_routes_exist(self) -> None:
        now = datetime(2025, 9, 27, 12, 0)
        self.mock_routes.list_all.return_value = []

        result = self.use_case.execute(ViewRoutesInProgressQuery(now=now))

        self.assertEqual(result, [])
        self.mock_routes.list_all.assert_called_once_with()

    def test_requires_in_progress_route_view_permission(self) -> None:
        now = datetime(2025, 9, 27, 12, 0)
        use_case = ViewRoutesInProgressUseCase(self.mock_routes, AuthorizationService(None))

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(ViewRoutesInProgressQuery(now=now))

        self.mock_routes.list_all.assert_not_called()
        self.assertEqual(len(use_case.pending_events), 1)
        event = cast(AuthorizationDenied, use_case.pending_events[0])
        self.assertIs(event.attempted_operation, AuthorizationOperation.ROUTE_LIST_IN_PROGRESS)
        self.assertIs(event.target_resource_type, AuditResourceType.ROUTE)
        self.assertIsNone(event.target_resource_id)
