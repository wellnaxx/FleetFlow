import unittest
from typing import cast
from unittest.mock import MagicMock

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.exceptions.application_errors import ValidationError
from src.application.queries.routes.view_all_routes import ViewAllRoutesQuery
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.pagination import PageQuery
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

        result = self.use_case.execute(ViewAllRoutesQuery())

        self.assertEqual(result.items, (r1, r2))
        self.assertIsInstance(result.items, tuple)
        self.assertIsNone(result.total)
        self.assertIsNone(result.limit)
        self.assertEqual(result.offset, 0)
        self.assertEqual(result.count, 2)
        self.mock_routes.list_all.assert_called_once_with()

    def test_returns_empty_list_when_no_routes(self) -> None:
        self.mock_routes.list_all.return_value = []

        result = self.use_case.execute(ViewAllRoutesQuery())

        self.assertEqual(result.items, ())
        self.assertEqual(result.count, 0)
        self.mock_routes.list_all.assert_called_once_with()

    def test_returns_requested_route_page(self) -> None:
        route = MagicMock()
        self.mock_routes.list_page.return_value = [route]

        result = self.use_case.execute(ViewAllRoutesQuery(page=PageQuery(limit=10, offset=20)))

        self.assertEqual(result.items, (route,))
        self.assertIsNone(result.total)
        self.assertEqual(result.limit, 10)
        self.assertEqual(result.offset, 20)
        self.assertEqual(result.count, 1)
        self.mock_routes.list_page.assert_called_once_with(limit=10, offset=20)
        self.mock_routes.list_all.assert_not_called()

    def test_rejects_invalid_pagination(self) -> None:
        with self.assertRaises(ValidationError):
            self.use_case.execute(ViewAllRoutesQuery(page=PageQuery(limit=0)))

        with self.assertRaises(ValidationError):
            self.use_case.execute(ViewAllRoutesQuery(page=PageQuery(limit=1, offset=-1)))

        with self.assertRaises(ValidationError):
            self.use_case.execute(ViewAllRoutesQuery(page=PageQuery(offset=1)))

        self.mock_routes.list_page.assert_not_called()

    def test_returns_requested_route_page_with_total(self) -> None:
        route = MagicMock()
        self.mock_routes.list_page_with_total.return_value = ([route], 3)

        result = self.use_case.execute(
            ViewAllRoutesQuery(
                page=PageQuery(limit=10, offset=20, include_total=True),
            )
        )

        self.assertEqual(result.items, (route,))
        self.assertEqual(result.total, 3)
        self.assertEqual(result.count, 1)
        self.mock_routes.list_page_with_total.assert_called_once_with(limit=10, offset=20)

    def test_requires_route_view_all_permission(self) -> None:
        use_case = ViewAllRoutesUseCase(self.mock_routes, AuthorizationService(None))

        with self.assertRaises(PermissionError):
            use_case.execute(ViewAllRoutesQuery())

        self.mock_routes.list_all.assert_not_called()
        self.assertEqual(len(use_case.pending_events), 1)
        event = cast(AuthorizationDenied, use_case.pending_events[0])
        self.assertIsInstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.ROUTE_LIST)
        self.assertIs(event.target_resource_type, AuditResourceType.ROUTE)
        self.assertIsNone(event.target_resource_id)
