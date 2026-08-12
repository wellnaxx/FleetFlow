"""Tests for the administrator password-reset workflow."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied, UserPasswordReset, UserPasswordResetRejected
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.password_errors import PasswordResetCriteriaNotMetError
from src.application.models.user_record import UserRecord
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.auth.reset_password import ResetPasswordUseCase
from src.domain.enums.auth import Permission
from tests.unit.application.use_cases.authz_helpers import employee_authz, manager_authz

NOW = datetime(2026, 1, 2, 3, 4)


def _user_record(user_id: int, username: str) -> UserRecord:
    return UserRecord(
        user_id=user_id,
        username=username,
        role="EMPLOYEE",
        name=username.title(),
        email="",
        phone_number="",
        password="HASH",
    )


class ResetPasswordUseCaseShould(unittest.TestCase):
    """Verify administrator resets, authorization, and event recording."""

    def test_resets_target_password_for_manager(self) -> None:
        auth = MagicMock()
        auth.reset_password.return_value = _user_record(42, "alice")
        use_case = ResetPasswordUseCase(auth, manager_authz(), clock=lambda: NOW)

        result = use_case.execute(username="  ALICE  ", new_password="NewSecret123")

        self.assertIsNone(result)
        auth.reset_password.assert_called_once_with("alice", "NewSecret123")
        auth.change_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordReset)
        assert isinstance(event, UserPasswordReset)
        self.assertEqual(event.user_id, 42)
        self.assertEqual(event.username, "alice")
        self.assertEqual(event.occurred_at, NOW)

    def test_rejects_blank_target_and_records_reset_rejection(self) -> None:
        auth = MagicMock()
        use_case = ResetPasswordUseCase(auth, manager_authz(), clock=lambda: NOW)

        with self.assertRaisesRegex(ValidationError, "non-empty"):
            use_case.execute(username="   ", new_password="NewSecret123")

        auth.reset_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordResetRejected)
        assert isinstance(event, UserPasswordResetRejected)
        self.assertIsNone(event.user_id)
        self.assertEqual(event.username, "   ")
        self.assertEqual(event.occurred_at, NOW)

    def test_requires_authenticated_principal(self) -> None:
        auth = MagicMock()
        use_case = ResetPasswordUseCase(auth, AuthorizationService(None), clock=lambda: NOW)

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(username="alice", new_password="NewSecret123")

        auth.reset_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertEqual(event.required_permissions, (Permission.ADMIN_USER,))
        self.assertIs(event.attempted_operation, AuthorizationOperation.USER_RESET_PASSWORD)
        self.assertIs(event.target_resource_type, AuditResourceType.USER)
        self.assertIsNone(event.target_resource_id)

    def test_authorizes_before_rejecting_blank_target(self) -> None:
        auth = MagicMock()
        use_case = ResetPasswordUseCase(auth, AuthorizationService(None), clock=lambda: NOW)

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(username="   ", new_password="NewSecret123")

        auth.reset_password.assert_not_called()
        self.assertEqual(len(use_case.pending_events), 1)
        self.assertIsInstance(use_case.pending_events[0], AuthorizationDenied)

    def test_requires_admin_permission_and_identifies_self_target(self) -> None:
        auth = MagicMock()
        use_case = ResetPasswordUseCase(auth, employee_authz(), clock=lambda: NOW)

        with self.assertRaisesRegex(PermissionError, "ADMIN_USER"):
            use_case.execute(username="employee", new_password="NewSecret123")

        auth.reset_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertEqual(event.target_resource_id, "2")

    def test_records_typed_reset_rejection_and_propagates_error(self) -> None:
        auth = MagicMock()
        expected = PasswordResetCriteriaNotMetError(
            "Password is too weak.",
            user_id=42,
            username="alice",
        )
        auth.reset_password.side_effect = expected
        use_case = ResetPasswordUseCase(auth, manager_authz(), clock=lambda: NOW)

        with self.assertRaises(PasswordResetCriteriaNotMetError) as raised:
            use_case.execute(username="alice", new_password="weak")

        self.assertIs(raised.exception, expected)
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordResetRejected)
        assert isinstance(event, UserPasswordResetRejected)
        self.assertEqual(event.user_id, 42)
        self.assertEqual(event.username, "alice")
        self.assertIs(event.reason, expected.reason)
        self.assertEqual(event.occurred_at, NOW)


if __name__ == "__main__":
    unittest.main()
