"""Tests for the self-service password-change CLI command."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_change_password import AuthChangePassword
from src.application.commands.auth.change_password import CHANGE_OWN_PASSWORD, ChangeOwnPasswordCommand
from src.ports.input.command_bus import CommandBus


class AuthChangePasswordShould(unittest.TestCase):
    """Verify prompting, validation, and command-bus dispatch."""

    def make_cmd(self, params: tuple[str, ...] = ()) -> tuple[AuthChangePassword, MagicMock]:
        """Build the CLI command with an isolated command-bus mock."""
        command_bus = MagicMock(spec=CommandBus)
        return AuthChangePassword(params, command_bus), command_bus

    def test_skips_heartbeat(self) -> None:
        self.assertTrue(AuthChangePassword.skips_heartbeat)

    def test_rejects_arguments_before_prompting(self) -> None:
        cmd, command_bus = self.make_cmd(("alice",))

        with self.assertRaisesRegex(ValueError, "does not accept arguments"):
            cmd.execute()

        command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_rejects_mismatched_confirmation(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd()
        getpass_mock.side_effect = ["OldPass123", "NewPass123", "Mismatch"]

        with self.assertRaisesRegex(ValueError, "Passwords do not match"):
            cmd.execute()

        command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_dispatches_typed_password_change_command(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd()
        getpass_mock.side_effect = ["OldPass123", "NewPass123", "NewPass123"]

        result = cmd.execute()

        self.assertEqual(result, "Password changed.")
        command_bus.dispatch.assert_called_once()
        self.assertIs(command_bus.dispatch.call_args.kwargs["key"], CHANGE_OWN_PASSWORD)
        command = command_bus.dispatch.call_args.kwargs["command"]
        self.assertIsInstance(command, ChangeOwnPasswordCommand)
        self.assertEqual(command.current_password, "OldPass123")
        self.assertEqual(command.new_password, "NewPass123")

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_propagates_command_bus_error(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd()
        getpass_mock.side_effect = ["OldPass123", "NewPass123", "NewPass123"]
        command_bus.dispatch.side_effect = PermissionError("Unauthenticated")

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            cmd.execute()

        command_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
