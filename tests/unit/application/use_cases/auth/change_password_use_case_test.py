import unittest
from unittest.mock import MagicMock

from src.application.use_cases.auth.change_password import ChangePasswordUseCase


class ChangePasswordUseCase_Should(unittest.TestCase):
    def test_reset_branch_calls_reset_password(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth)

        result = use_case.execute("alice", "NewSecret123")

        self.assertIsNone(result)
        auth.reset_password.assert_called_once_with("alice", "NewSecret123")
        auth.change_password.assert_not_called()

    def test_self_service_branch_calls_change_password(self) -> None:
        auth = MagicMock()
        use_case = ChangePasswordUseCase(auth)

        result = use_case.execute("alice", "NewSecret123", old_password="OldSecret123")

        self.assertIsNone(result)
        auth.change_password.assert_called_once_with("alice", "OldSecret123", "NewSecret123")
        auth.reset_password.assert_not_called()
