"""Tests for the login CLI command."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_login import AuthLogin
from src.application.commands.auth.login import LOGIN, LoginCommand
from src.ports.input.command_bus import CommandBus


class AuthLoginShould(unittest.TestCase):
    """Verify credential collection and typed command dispatch."""

    def make_cmd(self, params: tuple[str, ...] = ()) -> tuple[AuthLogin, MagicMock]:
        """Build the command with an isolated command-bus mock."""
        command_bus = MagicMock(spec=CommandBus)
        return AuthLogin(params, command_bus), command_bus

    @staticmethod
    def login_result(*, name: str, role: str) -> SimpleNamespace:
        """Build the principal shape rendered by the command."""
        return SimpleNamespace(principal=SimpleNamespace(name=name, role=SimpleNamespace(value=role)))

    def test_mutates_session(self) -> None:
        self.assertTrue(AuthLogin.mutates_session)

    def test_skips_heartbeat(self) -> None:
        self.assertTrue(AuthLogin.skips_heartbeat)

    @patch("src.adapters.driving.cli.commands.auth_login.getpass.getpass")
    def test_dispatches_supplied_username_and_password(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd((" alice ",))
        getpass_mock.return_value = "secretPW"
        command_bus.dispatch.return_value = self.login_result(name="Alice", role="ADMIN")

        result = cmd.execute()

        self.assertEqual(result, "Logged in as Alice [ADMIN]")
        getpass_mock.assert_called_once_with("Password: ")
        command_bus.dispatch.assert_called_once()
        self.assertIs(command_bus.dispatch.call_args.kwargs["key"], LOGIN)
        command = command_bus.dispatch.call_args.kwargs["command"]
        self.assertIsInstance(command, LoginCommand)
        self.assertEqual(command.username, "alice")
        self.assertEqual(command.password, "secretPW")

    @patch("src.adapters.driving.cli.commands.auth_login.getpass.getpass")
    @patch("builtins.input")
    def test_prompts_for_and_strips_missing_username(
        self,
        input_mock: MagicMock,
        getpass_mock: MagicMock,
    ) -> None:
        cmd, command_bus = self.make_cmd()
        input_mock.return_value = "  Bob\t"
        getpass_mock.return_value = "pw123456"
        command_bus.dispatch.return_value = self.login_result(name="Bob", role="USER")

        result = cmd.execute()

        self.assertEqual(result, "Logged in as Bob [USER]")
        input_mock.assert_called_once_with("Username: ")
        command = command_bus.dispatch.call_args.kwargs["command"]
        self.assertEqual(command.username, "Bob")
        self.assertEqual(command.password, "pw123456")

    @patch("src.adapters.driving.cli.commands.auth_login.getpass.getpass")
    def test_rejects_multiple_username_arguments_before_prompting(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("alice", "extra"))

        with self.assertRaisesRegex(ValueError, "at most one"):
            cmd.execute()

        getpass_mock.assert_not_called()
        command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.auth_login.getpass.getpass")
    def test_propagates_command_bus_failure(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("carol",))
        getpass_mock.return_value = "wrong"
        command_bus.dispatch.side_effect = ValueError("invalid credentials")

        with self.assertRaisesRegex(ValueError, "invalid credentials"):
            cmd.execute()

        command_bus.dispatch.assert_called_once()

    @patch("src.adapters.driving.cli.commands.auth_login.getpass.getpass")
    def test_forwards_blank_supplied_username_for_application_validation(
        self,
        getpass_mock: MagicMock,
    ) -> None:
        cmd, command_bus = self.make_cmd(("   ",))
        getpass_mock.return_value = "pw"
        command_bus.dispatch.return_value = self.login_result(name="", role="USER")

        cmd.execute()

        command = command_bus.dispatch.call_args.kwargs["command"]
        self.assertEqual(command.username, "")


if __name__ == "__main__":
    unittest.main()
