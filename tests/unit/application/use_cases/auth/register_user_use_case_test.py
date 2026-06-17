import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.enums.user_registration_rejection_reasons import UserRegistrationRejectionReason
from src.application.events.auth_events import UserRegistered, UserRegistrationRejected
from src.application.exceptions.password_errors import (
    RegistrationInvalidUsernameError,
    RegistrationPasswordCriteriaNotMetError,
    RegistrationUsernameAlreadyExistsError,
)
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.domain.enums.auth import Role
from tests.unit.application.use_cases.authz_helpers import employee_authz, manager_authz


class RegisterUserUseCase_Should(unittest.TestCase):
    def test_delegates_to_auth_service_and_records_registration_event(self) -> None:
        auth = MagicMock()
        record = SimpleNamespace(username="alice", role=Role.MANAGER.value, user_id=1)
        auth.register_user.return_value = record
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = RegisterUserUseCase(auth, manager_authz(), clock=lambda: occurred_at)

        result = use_case.execute(
            username="alice",
            role=Role.MANAGER,
            name="Alice",
            email="alice@example.com",
            phone_number="0412345678",
            password="TempPass123",
        )

        self.assertIs(result, record)
        auth.register_user.assert_called_once_with(
            username="alice",
            role=Role.MANAGER,
            name="Alice",
            email="alice@example.com",
            phone_number="0412345678",
            password="TempPass123",
        )
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserRegistered)
        assert isinstance(event, UserRegistered)
        self.assertEqual(event.user_id, 1)
        self.assertEqual(event.username, "alice")
        self.assertIs(event.role, Role.MANAGER)
        self.assertEqual(event.occurred_at, occurred_at)

    def test_requires_admin_permission(self) -> None:
        auth = MagicMock()
        use_case = RegisterUserUseCase(auth, employee_authz())

        with self.assertRaises(PermissionError) as ctx:
            use_case.execute(
                username="alice",
                role=Role.EMPLOYEE,
                name="Alice",
                email="alice@example.com",
                phone_number="0412345678",
                password="TempPass123",
            )

        self.assertIn("ADMIN_USER", str(ctx.exception))
        auth.register_user.assert_not_called()

    def test_records_invalid_username_rejection_event(self) -> None:
        auth = MagicMock()
        auth.register_user.side_effect = RegistrationInvalidUsernameError(username=None)
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = RegisterUserUseCase(auth, manager_authz(), clock=lambda: occurred_at)

        with self.assertRaises(RegistrationInvalidUsernameError):
            use_case.execute(
                username=" ",
                role=Role.EMPLOYEE,
                name="Alice",
                email="alice@example.com",
                phone_number="0412345678",
                password="TempPass123",
            )

        self._assert_registration_rejection(
            use_case,
            username=None,
            reason=UserRegistrationRejectionReason.INVALID_USERNAME,
            occurred_at=occurred_at,
        )

    def test_records_duplicate_username_rejection_event(self) -> None:
        auth = MagicMock()
        auth.register_user.side_effect = RegistrationUsernameAlreadyExistsError(username="alice")
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = RegisterUserUseCase(auth, manager_authz(), clock=lambda: occurred_at)

        with self.assertRaises(RegistrationUsernameAlreadyExistsError):
            use_case.execute(
                username="alice",
                role=Role.EMPLOYEE,
                name="Alice",
                email="alice@example.com",
                phone_number="0412345678",
                password="TempPass123",
            )

        self._assert_registration_rejection(
            use_case,
            username="alice",
            reason=UserRegistrationRejectionReason.USERNAME_ALREADY_EXISTS,
            occurred_at=occurred_at,
        )

    def test_records_password_policy_rejection_event(self) -> None:
        auth = MagicMock()
        auth.register_user.side_effect = RegistrationPasswordCriteriaNotMetError(
            "Password must contain a special character.",
            username="alice",
        )
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = RegisterUserUseCase(auth, manager_authz(), clock=lambda: occurred_at)

        with self.assertRaises(RegistrationPasswordCriteriaNotMetError):
            use_case.execute(
                username="alice",
                role=Role.EMPLOYEE,
                name="Alice",
                email="alice@example.com",
                phone_number="0412345678",
                password="TempPass123",
            )

        self._assert_registration_rejection(
            use_case,
            username="alice",
            reason=UserRegistrationRejectionReason.PASSWORD_CRITERIA_NOT_MET,
            occurred_at=occurred_at,
        )

    def _assert_registration_rejection(
        self,
        use_case: RegisterUserUseCase,
        *,
        username: str | None,
        reason: UserRegistrationRejectionReason,
        occurred_at: datetime,
    ) -> None:
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserRegistrationRejected)
        assert isinstance(event, UserRegistrationRejected)
        self.assertEqual(event.username, username)
        self.assertIs(event.reason, reason)
        self.assertEqual(event.occurred_at, occurred_at)
