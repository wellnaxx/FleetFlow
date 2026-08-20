"""Tests for the administrative password-reset CLI command."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_reset_password import AuthResetPassword
from src.application.commands.auth.reset_password import RESET_USER_PASSWORD, ResetUserPasswordCommand
from src.ports.input.command_bus import CommandBus


class AuthResetPasswordShould(unittest.TestCase):
    """Verify target parsing, password prompting, and typed dispatch."""

    def make_cmd(self, params: tuple[str, ...]) -> tuple[AuthResetPassword, MagicMock]:
        """Build the command with an isolated command bus."""
        command_bus = MagicMock(spec=CommandBus)
        return AuthResetPassword(params, command_bus), command_bus

    def test_skips_heartbeat(self) -> None:
        self.assertTrue(AuthResetPassword.skips_heartbeat)

    def test_requires_exactly_one_username(self) -> None:
        for params in ((), ("alice", "extra")):
            with self.subTest(params=params):
                cmd, command_bus = self.make_cmd(params)

                with self.assertRaisesRegex(ValueError, "Usage"):
                    cmd.execute()

                command_bus.dispatch.assert_not_called()

    def test_rejects_blank_username(self) -> None:
        cmd, command_bus = self.make_cmd(("   ",))

        with self.assertRaisesRegex(ValueError, "non-empty"):
            cmd.execute()

        command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.auth_reset_password.getpass.getpass")
    def test_rejects_mismatched_confirmation(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("alice",))
        getpass_mock.side_effect = ["NewPass123", "Mismatch"]

        with self.assertRaisesRegex(ValueError, "Passwords do not match"):
            cmd.execute()

        command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.auth_reset_password.getpass.getpass")
    def test_normalizes_target_and_dispatches_command(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("  ALICE  ",))
        getpass_mock.side_effect = ["NewPass123", "NewPass123"]

        result = cmd.execute()

        self.assertEqual(result, "Password reset for 'alice'.")
        command_bus.dispatch.assert_called_once()
        self.assertIs(command_bus.dispatch.call_args.kwargs["key"], RESET_USER_PASSWORD)
        command = command_bus.dispatch.call_args.kwargs["command"]
        self.assertIsInstance(command, ResetUserPasswordCommand)
        self.assertEqual(command.username, "alice")
        self.assertEqual(command.new_password, "NewPass123")

    @patch("src.adapters.driving.cli.commands.auth_reset_password.getpass.getpass")
    def test_propagates_command_bus_failure(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("alice",))
        getpass_mock.side_effect = ["NewPass123", "NewPass123"]
        expected = PermissionError("Missing permission: ADMIN_USER")
        command_bus.dispatch.side_effect = expected

        with self.assertRaises(PermissionError) as raised:
            cmd.execute()

        self.assertIs(raised.exception, expected)
        command_bus.dispatch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
