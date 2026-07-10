import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.events.auth_events import AuthorizationDenied, UserSessionEnded, UserTokensRevoked
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.auth.logout import LogoutUseCase
from src.domain.enums.auth import Permission, Role


def _principal(username: str = "alice") -> CurrentUserPrincipal:
    return CurrentUserPrincipal(
        user_id=7,
        username=username,
        name="Alice",
        email="alice@example.com",
        phone_number="0412345678",
        role=Role.EMPLOYEE,
    )


class LogoutUseCase_Should(unittest.TestCase):
    def test_revokes_tokens_logs_out_and_records_events(self) -> None:
        auth = MagicMock()
        auth.current_user = _principal()
        authz = AuthorizationService(auth.current_user)
        user_repo = MagicMock()
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = LogoutUseCase(user_repo, auth, authz, clock=lambda: occurred_at)

        result = use_case.execute()

        self.assertIsNone(result)
        user_repo.increment_token_version_by_id.assert_called_once_with(7)
        auth.logout.assert_called_once_with()

        revoked, ended = use_case.pending_events
        self.assertIsInstance(revoked, UserTokensRevoked)
        assert isinstance(revoked, UserTokensRevoked)
        self.assertEqual(revoked.user_id, 7)
        self.assertEqual(revoked.username, "alice")
        self.assertIs(revoked.reason, TokenRevocationReason.USER_LOGOUT)
        self.assertEqual(revoked.occurred_at, occurred_at)

        self.assertIsInstance(ended, UserSessionEnded)
        assert isinstance(ended, UserSessionEnded)
        self.assertEqual(ended.user_id, 7)
        self.assertEqual(ended.username, "alice")
        self.assertEqual(ended.occurred_at, occurred_at)

    def test_does_not_clear_session_or_record_events_when_revocation_fails(self) -> None:
        auth = MagicMock()
        auth.current_user = _principal()
        authz = AuthorizationService(auth.current_user)
        user_repo = MagicMock()
        user_repo.increment_token_version_by_id.side_effect = RuntimeError("db failed")
        use_case = LogoutUseCase(user_repo, auth, authz)

        with self.assertRaises(RuntimeError):
            use_case.execute()

        auth.logout.assert_not_called()
        self.assertEqual(use_case.pending_events, ())

    def test_execute_requires_authenticated_user(self) -> None:
        auth = MagicMock()
        auth.current_user = None
        user_repo = MagicMock()
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = LogoutUseCase(user_repo, auth, AuthorizationService(None), clock=lambda: occurred_at)

        with self.assertRaises(PermissionError):
            use_case.execute()

        user_repo.increment_token_version_by_id.assert_not_called()
        auth.logout.assert_not_called()

        event = use_case.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.SESSION_END)
        self.assertIs(event.target_resource_type, AuditResourceType.USER)
        self.assertIsNone(event.target_resource_id)
        self.assertEqual(event.required_permissions, (Permission.AUTHENTICATED,))
        self.assertEqual(event.occurred_at, occurred_at)

    def test_execute_rejects_blank_authenticated_username_and_records_denial(self) -> None:
        auth = MagicMock()
        auth.current_user = _principal(username="   ")
        user_repo = MagicMock()
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = LogoutUseCase(
            user_repo,
            auth,
            AuthorizationService(auth.current_user),
            clock=lambda: occurred_at,
        )

        with self.assertRaises(PermissionError):
            use_case.execute()

        user_repo.increment_token_version_by_id.assert_not_called()
        auth.logout.assert_not_called()

        event = use_case.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.SESSION_END)
        self.assertIs(event.target_resource_type, AuditResourceType.USER)
        self.assertEqual(event.target_resource_id, "7")
        self.assertEqual(event.required_permissions, (Permission.AUTHENTICATED,))
        self.assertEqual(event.occurred_at, occurred_at)
