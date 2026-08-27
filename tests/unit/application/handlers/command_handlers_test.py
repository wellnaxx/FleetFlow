"""Unit tests for command-to-use-case argument adaptation."""

import unittest
from unittest.mock import MagicMock

from src.application.commands.state.save_world import SaveWorldCommand
from src.application.handlers.commands.state.save_world import SaveWorldCommandHandler


class CommandHandlersShould(unittest.TestCase):
    """Verify that command handlers delegate once with the intended arguments."""

    def test_save_world_delegates_path_and_returns_resolved_path(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = "C:/snapshots/world.json"

        result = SaveWorldCommandHandler(use_case).execute(SaveWorldCommand(path="world.json"))

        self.assertEqual(result, "C:/snapshots/world.json")
        use_case.execute.assert_called_once_with("world.json")


if __name__ == "__main__":
    unittest.main()
