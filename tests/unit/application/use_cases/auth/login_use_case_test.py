import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.enums.user_login_rejection_reasons import UserLoginRejectionReason
from src.application.events.auth_events import UserAuthenticated, UserLoginRejected
from src.application.exceptions.password_errors import LoginWrongPasswordError
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.use_cases.auth.login import LoginUseCase
from src.domain.enums.auth import Role


class LoginUseCase_Should(unittest.TestCase):
    def test_delegates_to_auth_service_and_records_authentication_event(self) -> None:
        auth = MagicMock()
        record = SimpleNamespace(user_id=10, username="alice")
        principal = CurrentUserPrincipal(
            user_id=10,
            username="alice",
            name="Alice",
            email="alice@example.com",
            phone_number="0412345678",
            role=Role.EMPLOYEE,
        )
        auth.login.return_value = (principal, record)
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = LoginUseCase(auth, clock=lambda: occurred_at)

        result = use_case.execute("alice", "Secret123")

        self.assertIs(result.record, record)
        self.assertIs(result.principal, principal)
        auth.login.assert_called_once_with("alice", "Secret123")

        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserAuthenticated)
        assert isinstance(event, UserAuthenticated)
        self.assertEqual(event.user_id, 10)
        self.assertEqual(event.username, "alice")
        self.assertIs(event.role, Role.EMPLOYEE)
        self.assertEqual(event.occurred_at, occurred_at)

    def test_records_login_rejection_event_and_reraises(self) -> None:
        auth = MagicMock()
        auth.login.side_effect = LoginWrongPasswordError(user_id=10, username="alice")
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = LoginUseCase(auth, clock=lambda: occurred_at)

        with self.assertRaises(LoginWrongPasswordError):
            use_case.execute("alice", "wrong")

        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserLoginRejected)
        assert isinstance(event, UserLoginRejected)
        self.assertEqual(event.user_id, 10)
        self.assertEqual(event.username, "alice")
        self.assertIs(event.reason, UserLoginRejectionReason.INVALID_PASSWORD)
        self.assertEqual(event.occurred_at, occurred_at)
