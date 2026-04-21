import unittest
from unittest.mock import MagicMock

from src.application.use_cases.auth.logout import LogoutUseCase


class LogoutUseCase_Should(unittest.TestCase):
    def test_delegates_to_auth_service(self) -> None:
        auth = MagicMock()
        use_case = LogoutUseCase(auth)

        result = use_case.execute()

        self.assertIsNone(result)
        auth.logout.assert_called_once_with()
