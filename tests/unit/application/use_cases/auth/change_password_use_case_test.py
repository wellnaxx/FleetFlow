import unittest
from unittest.mock import MagicMock

from src.application.exceptions.application_errors import ValidationError
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from tests.unit.application.use_cases.authz_helpers import employee_authz, manager_authz


class ChangePasswordUseCase_Should(unittest.TestCase):
    def test_reset_branch_calls_reset_password(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth, manager_authz())

        result = use_case.execute("alice", "NewSecret123")

        self.assertIsNone(result)
        auth.reset_password.assert_called_once_with("alice", "NewSecret123")
        auth.change_password.assert_not_called()

    def test_self_service_branch_calls_change_password(self) -> None:
        auth = MagicMock()
        auth.last_username = "alice"
        use_case = ChangePasswordUseCase(auth, manager_authz())

        result = use_case.execute("alice", "NewSecret123", old_password="OldSecret123")

        self.assertIsNone(result)
        auth.change_password.assert_called_once_with("alice", "OldSecret123", "NewSecret123")
        auth.reset_password.assert_not_called()

    def test_self_service_branch_rejects_other_users_without_admin_permission(self) -> None:
        auth = MagicMock()
        auth.last_username = "alice"
        use_case = ChangePasswordUseCase(auth, employee_authz())

        with self.assertRaises(PermissionError) as ctx:
            use_case.execute("bob", "NewSecret123", old_password="OldSecret123")

        self.assertIn("another user's password", str(ctx.exception))
        auth.change_password.assert_not_called()

    def test_current_user_branch_uses_explicit_username(self) -> None:
        auth = MagicMock()
        auth.last_username = "alice"
        use_case = ChangePasswordUseCase(auth, employee_authz())

        result = use_case.execute_current_user(
            " Alice ",
            "NewSecret123",
            old_password="OldSecret123",
        )

        self.assertIsNone(result)
        auth.change_password.assert_called_once_with("alice", "OldSecret123", "NewSecret123")
        auth.reset_password.assert_not_called()

    def test_current_user_branch_rejects_username_mismatch(self) -> None:
        auth = MagicMock()
        auth.last_username = "alice"
        use_case = ChangePasswordUseCase(auth, employee_authz())

        with self.assertRaises(PermissionError) as ctx:
            use_case.execute_current_user("bob", "NewSecret123", old_password="OldSecret123")

        self.assertIn("Username does not match authenticated user.", str(ctx.exception))
        auth.change_password.assert_not_called()

    def test_current_user_branch_requires_authenticated_user(self) -> None:
        auth = MagicMock()
        auth.last_username = "alice"
        use_case = ChangePasswordUseCase(auth, AuthorizationService(None))

        with self.assertRaises(PermissionError) as ctx:
            use_case.execute_current_user("alice", "NewSecret123", old_password="OldSecret123")

        self.assertIn("Unauthenticated", str(ctx.exception))
        auth.change_password.assert_not_called()

    def test_current_user_branch_requires_username(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth, employee_authz())

        with self.assertRaises(PermissionError) as ctx:
            use_case.execute_current_user(None, "NewSecret123", old_password="OldSecret123")

        self.assertIn("no username", str(ctx.exception))
        auth.change_password.assert_not_called()

    def test_rejects_blank_target_username(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth, manager_authz())

        with self.assertRaises(ValidationError) as ctx:
            use_case.execute("   ", "NewSecret123")

        self.assertIn("Username must be a non-empty string.", str(ctx.exception))
        auth.reset_password.assert_not_called()
        auth.change_password.assert_not_called()
