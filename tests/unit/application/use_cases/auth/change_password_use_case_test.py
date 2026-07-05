import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.events.auth_events import AuthorizationDenied, UserPasswordChanged, UserPasswordReset
from src.application.exceptions.application_errors import ValidationError
from src.application.models.user_record import UserRecord
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.domain.enums.auth import Permission
from tests.unit.application.use_cases.authz_helpers import employee_authz, manager_authz


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


class ChangePasswordUseCase_Should(unittest.TestCase):
    def test_reset_branch_calls_reset_password(self) -> None:
        auth = MagicMock()
        now = datetime(2026, 1, 2, 3, 4)
        auth.reset_password.return_value = _user_record(42, "alice")
        use_case = ChangePasswordUseCase(auth, manager_authz(), clock=lambda: now)

        result = use_case.execute("alice", "NewSecret123")

        self.assertIsNone(result)
        auth.reset_password.assert_called_once_with("alice", "NewSecret123")
        auth.change_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordReset)
        assert isinstance(event, UserPasswordReset)
        self.assertEqual(event.user_id, 42)
        self.assertEqual(event.username, "alice")
        self.assertEqual(event.occurred_at, now)

    def test_self_service_branch_calls_change_password(self) -> None:
        auth = MagicMock()
        now = datetime(2026, 1, 2, 3, 4)
        auth.change_password.return_value = _user_record(42, "alice")
        use_case = ChangePasswordUseCase(auth, manager_authz(), clock=lambda: now)

        result = use_case.execute("alice", "NewSecret123", old_password="OldSecret123")

        self.assertIsNone(result)
        auth.change_password.assert_called_once_with("alice", "OldSecret123", "NewSecret123")
        auth.reset_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordChanged)
        assert isinstance(event, UserPasswordChanged)
        self.assertEqual(event.user_id, 42)
        self.assertEqual(event.username, "alice")
        self.assertEqual(event.occurred_at, now)

    def test_self_service_branch_rejects_other_users_without_admin_permission(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth, employee_authz())

        with self.assertRaises(PermissionError) as ctx:
            use_case.execute("bob", "NewSecret123", old_password="OldSecret123")

        self.assertIn("another user's password", str(ctx.exception))
        auth.change_password.assert_not_called()

    def test_current_user_branch_uses_authenticated_principal_username(self) -> None:
        auth = MagicMock()
        now = datetime(2026, 1, 2, 3, 4)
        auth.change_password.return_value = _user_record(2, "employee")
        use_case = ChangePasswordUseCase(auth, employee_authz(), clock=lambda: now)

        result = use_case.execute_current_user(
            "NewSecret123",
            old_password="OldSecret123",
        )

        self.assertIsNone(result)
        auth.change_password.assert_called_once_with("employee", "OldSecret123", "NewSecret123")
        auth.reset_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordChanged)
        assert isinstance(event, UserPasswordChanged)
        self.assertEqual(event.user_id, 2)
        self.assertEqual(event.username, "employee")
        self.assertEqual(event.occurred_at, now)

    def test_current_user_branch_requires_authenticated_user(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth, AuthorizationService(None))

        with self.assertRaises(PermissionError) as ctx:
            use_case.execute_current_user("NewSecret123", old_password="OldSecret123")

        self.assertIn("Unauthenticated", str(ctx.exception))
        auth.change_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertIsNone(event.user_id)
        self.assertEqual(event.required_permissions, (Permission.AUTHENTICATED,))

    def test_rejects_blank_target_username(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth, manager_authz())

        with self.assertRaises(ValidationError) as ctx:
            use_case.execute("   ", "NewSecret123")

        self.assertIn("Username must be a non-empty string.", str(ctx.exception))
        auth.reset_password.assert_not_called()
        auth.change_password.assert_not_called()
