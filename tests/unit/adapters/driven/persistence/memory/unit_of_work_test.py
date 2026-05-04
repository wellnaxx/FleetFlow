import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.memory.unit_of_work import InMemoryUnitOfWork


class InMemoryUnitOfWork_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.routes = MagicMock()
        self.packages = MagicMock()
        self.trucks = MagicMock()
        self.unit_of_work = InMemoryUnitOfWork(self.routes, self.packages, self.trucks)

    def test_exposes_repositories_passed_to_constructor(self) -> None:
        self.assertIs(self.unit_of_work.routes, self.routes)
        self.assertIs(self.unit_of_work.packages, self.packages)
        self.assertIs(self.unit_of_work.trucks, self.trucks)

    def test_enter_returns_self(self) -> None:
        with self.unit_of_work as active:
            self.assertIs(active, self.unit_of_work)

    def test_exit_does_not_rollback_when_no_exception_occurred(self) -> None:
        with patch.object(self.unit_of_work, "rollback") as rollback_mock:
            self.unit_of_work.__exit__(None, None, None)

        rollback_mock.assert_not_called()

    def test_exit_rolls_back_when_exception_occurred(self) -> None:
        error = RuntimeError("failure")

        with patch.object(self.unit_of_work, "rollback") as rollback_mock:
            self.unit_of_work.__exit__(RuntimeError, error, None)

        rollback_mock.assert_called_once_with()

    def test_commit_is_noop(self) -> None:
        self.assertIsNone(self.unit_of_work.commit())

    def test_rollback_is_noop(self) -> None:
        self.assertIsNone(self.unit_of_work.rollback())
