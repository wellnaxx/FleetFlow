"""Tests for the authorized use-case base contract."""

import unittest
from typing import cast

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission


class _ProtectedUseCase(AuthorizedUseCase[None]):
    """Minimal protected use case used to exercise the base contract."""

    @requires(
        Permission.ROUTE_VIEW,
        operation=AuthorizationOperation.ROUTE_VIEW,
        target_resource_type=AuditResourceType.ROUTE,
        target_resource_id_resolver=None,
    )
    def execute(self) -> None:
        """Execute the protected operation after authorization."""


class AuthorizedUseCaseShould(unittest.TestCase):
    """Validate centralized authorization-event recording behavior."""

    def test_record_authorization_denial_on_the_use_case(self) -> None:
        use_case = _ProtectedUseCase(AuthorizationService(current_user=None))

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute()

        self.assertEqual(len(use_case.pending_events), 1)
        event = cast(AuthorizationDenied, use_case.pending_events[0])
        self.assertIsInstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.ROUTE_VIEW)
        self.assertEqual(event.required_permissions, (Permission.ROUTE_VIEW,))

    def test_keep_pending_event_buffers_isolated_between_instances(self) -> None:
        first = _ProtectedUseCase(AuthorizationService(current_user=None))
        second = _ProtectedUseCase(AuthorizationService(current_user=None))

        with self.assertRaises(PermissionError):
            first.execute()

        self.assertEqual(len(first.pending_events), 1)
        self.assertEqual(second.pending_events, ())


if __name__ == "__main__":
    unittest.main()
