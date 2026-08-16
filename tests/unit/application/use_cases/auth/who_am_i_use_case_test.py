"""Tests for the directly dispatchable current-principal query use case."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.queries.auth.who_am_i import WhoAmIQuery
from src.application.use_cases.auth.who_am_i import WhoAmIUseCase


class WhoAmIUseCaseShould(unittest.TestCase):
    """Verify current-principal lookup through the typed query contract."""

    def test_returns_current_user(self) -> None:
        auth = MagicMock()
        auth.current_user = SimpleNamespace(name="Manager")
        use_case = WhoAmIUseCase(auth)

        result = use_case.execute(WhoAmIQuery())

        self.assertIs(result, auth.current_user)

    def test_returns_none_when_not_logged_in(self) -> None:
        auth = MagicMock()
        auth.current_user = None
        use_case = WhoAmIUseCase(auth)

        self.assertIsNone(use_case.execute(WhoAmIQuery()))


if __name__ == "__main__":
    unittest.main()
