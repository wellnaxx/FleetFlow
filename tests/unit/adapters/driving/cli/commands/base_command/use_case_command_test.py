import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand


class _DummyUseCaseCommand(UseCaseCommand[object]):
    def execute(self) -> str:
        return "ok"


class UseCaseCommand_Should(unittest.TestCase):
    def test_exposes_use_case(self) -> None:
        app_data = MagicMock()
        auth = MagicMock()
        uc = object()

        cmd = _DummyUseCaseCommand(["a", "b"], app_data, auth, uc)

        self.assertIs(cmd.use_case, uc)
        self.assertEqual(cmd.params, ("a", "b"))
        self.assertIs(cmd.app_data, app_data)
        self.assertIs(cmd.auth, auth)
