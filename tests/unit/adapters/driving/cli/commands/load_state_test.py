"""Tests for the command-bus-backed world-state load CLI adapter."""

import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.load_state import LoadState
from src.application.commands.state.load_world import LOAD_WORLD, LoadWorldCommand
from src.ports.input.command_bus import CommandBus


class LoadStateShould(unittest.TestCase):
    """Verify argument handling, dispatch, rendering, and failure propagation."""

    def setUp(self) -> None:
        """Create an isolated command bus for each test."""
        self.command_bus = MagicMock(spec=CommandBus)

    def make_command(self, *params: str) -> LoadState:
        """Build the adapter with the supplied raw CLI parameters."""
        return LoadState(params, self.command_bus)

    def test_declares_runtime_mutation_without_autosave_or_heartbeat(self) -> None:
        self.assertTrue(LoadState.mutates_state)
        self.assertFalse(LoadState.autosaves_state)
        self.assertTrue(LoadState.skips_heartbeat)

    def test_dispatches_explicit_path_and_renders_resolved_path(self) -> None:
        self.command_bus.dispatch.return_value = "/abs/state-2025-09-01.json"

        result = self.make_command("/data/snapshots/state-2025-09-01.json").execute()

        self.assertEqual(result, "Loaded state from /abs/state-2025-09-01.json")
        self.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path="/data/snapshots/state-2025-09-01.json"),
        )

    def test_dispatches_default_path_when_omitted(self) -> None:
        self.command_bus.dispatch.return_value = "/abs/state.json"

        result = self.make_command().execute()

        self.assertEqual(result, "Loaded state from /abs/state.json")
        self.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path="state.json"),
        )

    def test_rejects_more_than_one_path_before_dispatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "Expected between 0 and 1"):
            self.make_command("one.json", "two.json").execute()

        self.command_bus.dispatch.assert_not_called()

    def test_propagates_permission_error_from_command_bus(self) -> None:
        self.command_bus.dispatch.side_effect = PermissionError("Missing permission: APP_LOAD_STATE")

        with self.assertRaisesRegex(PermissionError, "APP_LOAD_STATE"):
            self.make_command("state.json").execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path="state.json"),
        )

    def test_propagates_command_bus_failure(self) -> None:
        self.command_bus.dispatch.side_effect = RuntimeError("load failed")

        with self.assertRaisesRegex(RuntimeError, "load failed"):
            self.make_command("state.json").execute()

        self.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path="state.json"),
        )


if __name__ == "__main__":
    unittest.main()
