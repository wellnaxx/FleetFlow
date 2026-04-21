import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.use_cases.auth.who_am_i import WhoAmIUseCase


class WhoAmIUseCase_Should(unittest.TestCase):
    def test_returns_current_user(self) -> None:
        auth = MagicMock()
        auth.current_user = SimpleNamespace(name="Manager")
        use_case = WhoAmIUseCase(auth)

        result = use_case.execute()

        self.assertIs(result, auth.current_user)

    def test_returns_none_when_not_logged_in(self) -> None:
        auth = MagicMock()
        auth.current_user = None
        use_case = WhoAmIUseCase(auth)

        self.assertIsNone(use_case.execute())
