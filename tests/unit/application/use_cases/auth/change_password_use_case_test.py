"""Tests for the self-service password-change workflow."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.commands.auth.change_password import ChangeOwnPasswordCommand
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.user_password_change_rejection_reasons import UserPasswordChangeRejectionReason
from src.application.events.auth_events import (
    AuthorizationDenied,
    UserPasswordChanged,
    UserPasswordChangeRejected,
)
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.password_errors import CurrentPasswordIncorrectError
from src.application.models.user_record import UserRecord
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.domain.enums.auth import Permission
from tests.unit.application.use_cases.authz_helpers import employee_authz, principal

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


class ChangePasswordUseCaseShould(unittest.TestCase):
    """Verify current-principal password changes and event recording."""

    @staticmethod
    def command(
        current_password: str = "OldSecret123",
        new_password: str = "NewSecret123",
    ) -> ChangeOwnPasswordCommand:
        """Build a password-change command for use-case tests."""
        return ChangeOwnPasswordCommand(
            current_password=current_password,
            new_password=new_password,
        )

    def test_changes_authenticated_principal_password(self) -> None:
        auth = MagicMock()
        auth.change_password.return_value = _user_record(2, "employee")
        use_case = ChangePasswordUseCase(auth, employee_authz(), clock=lambda: NOW)

        result = use_case.execute(self.command())

        self.assertIsNone(result)
        auth.change_password.assert_called_once_with("employee", "OldSecret123", "NewSecret123")
        auth.reset_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordChanged)
        assert isinstance(event, UserPasswordChanged)
        self.assertEqual(event.user_id, 2)
        self.assertEqual(event.username, "employee")
        self.assertEqual(event.occurred_at, NOW)

    def test_requires_authenticated_principal(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth, AuthorizationService(None), clock=lambda: NOW)

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(self.command())

        auth.change_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.USER_CHANGE_PASSWORD)
        self.assertIs(event.target_resource_type, AuditResourceType.USER)
        self.assertIsNone(event.target_resource_id)
        self.assertEqual(event.required_permissions, (Permission.AUTHENTICATED,))
        self.assertEqual(event.occurred_at, NOW)

    def test_rejects_blank_normalized_principal_username(self) -> None:
        auth = MagicMock()
        authz = AuthorizationService(principal(2, "   "))
        use_case = ChangePasswordUseCase(auth, authz, clock=lambda: NOW)

        with self.assertRaisesRegex(ValidationError, "non-empty"):
            use_case.execute(self.command())

        auth.change_password.assert_not_called()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordChangeRejected)
        assert isinstance(event, UserPasswordChangeRejected)
        self.assertEqual(event.user_id, 2)
        self.assertEqual(event.username, "   ")
        self.assertIs(event.reason, UserPasswordChangeRejectionReason.INVALID_USERNAME)
        self.assertEqual(event.occurred_at, NOW)

    def test_records_typed_authentication_rejection_and_propagates_error(self) -> None:
        auth = MagicMock()
        expected = CurrentPasswordIncorrectError(user_id=2, username="employee")
        auth.change_password.side_effect = expected
        use_case = ChangePasswordUseCase(auth, employee_authz(), clock=lambda: NOW)

        with self.assertRaises(CurrentPasswordIncorrectError) as raised:
            use_case.execute(self.command(current_password="wrong"))

        self.assertIs(raised.exception, expected)
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserPasswordChangeRejected)
        assert isinstance(event, UserPasswordChangeRejected)
        self.assertEqual(event.user_id, 2)
        self.assertEqual(event.username, "employee")
        self.assertIs(event.reason, expected.reason)
        self.assertEqual(event.occurred_at, NOW)


if __name__ == "__main__":
    unittest.main()
