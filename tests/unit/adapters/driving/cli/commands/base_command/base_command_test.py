import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand


class _DummyCommand(BaseCommand[object]):
    def execute(self) -> str:
        return "ok"


class BaseCommandShould(unittest.TestCase):
    def test_exposes_constructor_dependencies(self) -> None:
        auth = MagicMock()
        authz = MagicMock()
        use_case = object()

        cmd = _DummyCommand(["a", "b"], auth, authz, use_case)

        self.assertIs(cmd.use_case, use_case)
        self.assertEqual(cmd.params, ("a", "b"))
        self.assertIs(cmd.auth, auth)
        self.assertIs(cmd.authz, authz)

    def test_defaults_mutation_flags_to_false(self) -> None:
        auth = MagicMock()
        authz = MagicMock()

        cmd = _DummyCommand([], auth, authz, object())

        self.assertFalse(cmd.mutates_state)
        self.assertFalse(cmd.mutates_session)
        self.assertFalse(cmd.skips_heartbeat)
        self.assertFalse(cmd.autosaves_state)
