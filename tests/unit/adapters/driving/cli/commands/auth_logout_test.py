"""Tests for the logout CLI command."""

import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.auth_logout import AuthLogout
from src.application.commands.auth.logout import LOGOUT, LogoutCommand
from src.ports.input.command_bus import CommandBus


class AuthLogoutShould(unittest.TestCase):
    """Verify logout metadata, argument validation, and typed dispatch."""

    def make_cmd(self, params: tuple[str, ...] = ()) -> tuple[AuthLogout, MagicMock]:
        """Build the command with an isolated command-bus mock."""
        command_bus = MagicMock(spec=CommandBus)
        return AuthLogout(params, command_bus), command_bus

    def test_mutates_session(self) -> None:
        self.assertTrue(AuthLogout.mutates_session)

    def test_skips_heartbeat(self) -> None:
        self.assertTrue(AuthLogout.skips_heartbeat)

    def test_dispatches_logout_command_and_returns_message(self) -> None:
        cmd, command_bus = self.make_cmd()

        result = cmd.execute()

        self.assertEqual(result, "Logged out.")
        command_bus.dispatch.assert_called_once()
        self.assertIs(command_bus.dispatch.call_args.kwargs["key"], LOGOUT)
        self.assertIsInstance(command_bus.dispatch.call_args.kwargs["command"], LogoutCommand)

    def test_propagates_command_bus_failure(self) -> None:
        cmd, command_bus = self.make_cmd()
        command_bus.dispatch.side_effect = RuntimeError("session not found")

        with self.assertRaisesRegex(RuntimeError, "session not found"):
            cmd.execute()

        command_bus.dispatch.assert_called_once()

    def test_rejects_arguments_before_dispatch(self) -> None:
        cmd, command_bus = self.make_cmd(("extra",))

        with self.assertRaisesRegex(ValueError, "does not accept arguments"):
            cmd.execute()

        command_bus.dispatch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
