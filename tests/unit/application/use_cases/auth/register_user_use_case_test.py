import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.domain.enums.auth import Role


class RegisterUserUseCase_Should(unittest.TestCase):
    def test_delegates_to_auth_service(self) -> None:
        auth = MagicMock()
        record = SimpleNamespace(username="alice", role=Role.MANAGER, user_id=1)
        auth.register_user.return_value = record
        use_case = RegisterUserUseCase(auth)

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
