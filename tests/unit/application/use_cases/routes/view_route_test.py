import unittest
from typing import cast
from unittest.mock import MagicMock

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.exceptions.application_errors import NotFoundError
from src.application.queries.routes.view_route import ViewRouteQuery
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = ViewRouteUseCase(self.mock_routes, manager_authz())

    def test_returns_route_when_found(self) -> None:
        route = MagicMock()
        route.route_id = 12
        self.mock_routes.get_by_id.return_value = route

        result = self.use_case.execute(ViewRouteQuery(route_id=12))

        self.assertIs(result, route)
        self.mock_routes.get_by_id.assert_called_once_with(12)

    def test_raises_when_route_not_found(self) -> None:
        self.mock_routes.get_by_id.return_value = None

        with self.assertRaises(NotFoundError) as ctx:
            self.use_case.execute(ViewRouteQuery(route_id=77))

        self.assertIn("Route with ID 77 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(77)

    def test_records_targeted_authorization_denial_before_repository_access(self) -> None:
        use_case = ViewRouteUseCase(self.mock_routes, AuthorizationService(None))

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(ViewRouteQuery(route_id=12))

        self.mock_routes.get_by_id.assert_not_called()
        self.assertEqual(len(use_case.pending_events), 1)
        event = cast(AuthorizationDenied, use_case.pending_events[0])
        self.assertIsInstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.ROUTE_VIEW)
        self.assertIs(event.target_resource_type, AuditResourceType.ROUTE)
        self.assertEqual(event.target_resource_id, "12")
