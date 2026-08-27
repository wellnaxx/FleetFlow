"""Tests for the command-bus-backed world-state save CLI adapter."""

import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.save_state import SaveState
from src.application.commands.state.save_world import SAVE_WORLD, SaveWorldCommand
from src.ports.input.command_bus import CommandBus


class SaveStateShould(unittest.TestCase):
    """Verify argument handling, dispatch, rendering, and failure propagation."""

    def setUp(self) -> None:
        """Create an isolated command bus for each test."""
        self.command_bus = MagicMock(spec=CommandBus)

    def make_command(self, *params: str) -> SaveState:
        """Build the adapter with the supplied raw CLI parameters."""
        return SaveState(params, self.command_bus)

    def test_declares_no_runtime_mutation_or_automatic_follow_up_save(self) -> None:
        self.assertFalse(SaveState.mutates_state)
        self.assertFalse(SaveState.autosaves_state)

    def test_dispatches_explicit_path_and_renders_resolved_path(self) -> None:
        self.command_bus.dispatch.return_value = "/abs/state-01.json"

        result = self.make_command("/tmp/state-01.json").execute()

        self.assertEqual(result, "Saved state to /abs/state-01.json")
        self.command_bus.dispatch.assert_called_once_with(
            key=SAVE_WORLD,
            command=SaveWorldCommand(path="/tmp/state-01.json"),
        )

    def test_dispatches_default_path_when_omitted(self) -> None:
        self.command_bus.dispatch.return_value = "/abs/state.json"

        result = self.make_command().execute()

        self.assertEqual(result, "Saved state to /abs/state.json")
        self.command_bus.dispatch.assert_called_once_with(
            key=SAVE_WORLD,
            command=SaveWorldCommand(path="state.json"),
        )

    def test_rejects_more_than_one_path_before_dispatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "Expected between 0 and 1"):
            self.make_command("one.json", "two.json").execute()

        self.command_bus.dispatch.assert_not_called()

    def test_propagates_permission_error_from_command_bus(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: APP_SAVE_STATE")

        with self.assertRaisesRegex(PermissionError, "APP_SAVE_STATE"):
            self.make_command("state.json").execute()

        self._assert_state_save_dispatched()

    def test_propagates_command_bus_failure(self) -> None:
        self.command_bus.dispatch.side_effect = RuntimeError("save failed")

        with self.assertRaisesRegex(RuntimeError, "save failed"):
            self.make_command("state.json").execute()

        self._assert_state_save_dispatched()

    def _assert_state_save_dispatched(self) -> None:
        """Assert dispatch of the canonical save command for the test path."""
        self.command_bus.dispatch.assert_called_once_with(
            key=SAVE_WORLD,
            command=SaveWorldCommand(path="state.json"),
        )


if __name__ == "__main__":
    unittest.main()
