import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.use_cases.auth.login import LoginUseCase


class LoginUseCase_Should(unittest.TestCase):
    def test_delegates_to_auth_service(self) -> None:
        auth = MagicMock()
        user = SimpleNamespace(name="Alice")
        auth.login.return_value = user
        use_case = LoginUseCase(auth)

        result = use_case.execute("alice", "Secret123")

        self.assertIs(result, user)
        auth.login.assert_called_once_with("alice", "Secret123")
