import unittest

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand


class _DummyCommand(BaseCommand[object]):
    def execute(self) -> str:
        return "ok"


class BaseCommandShould(unittest.TestCase):
    def test_exposes_constructor_dependencies(self) -> None:
        dependency = object()

        cmd = _DummyCommand(["a", "b"], dependency)

        self.assertIs(cmd.dependency, dependency)
        self.assertEqual(cmd.params, ("a", "b"))

    def test_defaults_mutation_flags_to_false(self) -> None:
        cmd = _DummyCommand([], object())

        self.assertFalse(cmd.mutates_state)
        self.assertFalse(cmd.mutates_session)
        self.assertFalse(cmd.skips_heartbeat)
        self.assertFalse(cmd.autosaves_state)
