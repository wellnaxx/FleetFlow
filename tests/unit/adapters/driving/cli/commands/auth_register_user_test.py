"""Tests for the user-registration CLI command."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_register import AuthRegisterUser
from src.application.commands.auth.register_user import REGISTER_USER, RegisterUserCommand
from src.domain.enums.auth import Role
from src.ports.input.command_bus import CommandBus


class AuthRegisterUserShould(unittest.TestCase):
    """Verify registration input collection and typed command dispatch."""

    def make_cmd(self, params: tuple[str, ...] = ()) -> tuple[AuthRegisterUser, MagicMock]:
        """Build a registration command with an isolated command bus."""
        command_bus = MagicMock(spec=CommandBus)
        return AuthRegisterUser(params, command_bus), command_bus

    def test_skips_heartbeat_without_mutating_session(self) -> None:
        self.assertTrue(AuthRegisterUser.skips_heartbeat)
        self.assertFalse(getattr(AuthRegisterUser, "mutates_session", False))

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_prompt_mode_dispatches_all_fields(self, input_mock: MagicMock, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd()
        input_mock.side_effect = [
            "  Alice  ",
            "  MANager ",
            " Alice Wonder ",
            "  alice@example.com ",
            "  0412345678  ",
        ]
        getpass_mock.side_effect = ["TempPass123", "TempPass123"]
        command_bus.dispatch.return_value = SimpleNamespace(
            username="alice", role=Role.MANAGER.value, user_id=101
        )

        result = cmd.execute()

        self.assertEqual(result, "Created MANAGER user 'alice' (id=101).")
        self._assert_dispatched(
            command_bus,
            username="  Alice  ",
            role=Role.MANAGER,
            name="Alice Wonder",
            email="alice@example.com",
            phone_number="0412345678",
            password="TempPass123",
        )

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    def test_hybrid_mode_dispatches_supplied_fields(self, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("Bob", "employee", "Bob B.", "bob@example.com", "0411222333"))
        getpass_mock.side_effect = ["SuperStrong1", "SuperStrong1"]
        command_bus.dispatch.return_value = SimpleNamespace(
            username="bob", role=Role.EMPLOYEE.value, user_id=202
        )

        result = cmd.execute()

        self.assertEqual(result, "Created EMPLOYEE user 'bob' (id=202).")
        self._assert_dispatched(
            command_bus,
            username="Bob",
            role=Role.EMPLOYEE,
            name="Bob B.",
            email="bob@example.com",
            phone_number="0411222333",
            password="SuperStrong1",
        )

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_accepts_role_prefix_and_empty_optional_fields(
        self, input_mock: MagicMock, getpass_mock: MagicMock
    ) -> None:
        cmd, command_bus = self.make_cmd(("carol", "MAN", "Carol C."))
        input_mock.side_effect = ["", ""]
        getpass_mock.side_effect = ["Pa55word!!", "Pa55word!!"]
        command_bus.dispatch.return_value = SimpleNamespace(
            username="carol", role=Role.MANAGER.value, user_id=303
        )

        cmd.execute()

        command = command_bus.dispatch.call_args.kwargs["command"]
        self.assertIs(command.role, Role.MANAGER)
        self.assertEqual(command.email, "")
        self.assertEqual(command.phone_number, "")

    @patch("builtins.input")
    def test_rejects_invalid_role_before_password_prompt(self, input_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("dave", "lead", "Dave D."))
        input_mock.side_effect = ["", ""]

        with self.assertRaisesRegex(ValueError, "Role must be"):
            cmd.execute()

        command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_rejects_mismatched_passwords(self, input_mock: MagicMock, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("erin", "employee", "Erin E."))
        input_mock.side_effect = ["", ""]
        getpass_mock.side_effect = ["Temp1234", "Mismatch1234"]

        with self.assertRaisesRegex(ValueError, "Passwords do not match"):
            cmd.execute()

        command_bus.dispatch.assert_not_called()

    def test_rejects_more_than_five_arguments(self) -> None:
        cmd, command_bus = self.make_cmd(("a", "employee", "A", "e", "p", "extra"))

        with self.assertRaisesRegex(ValueError, "Usage"):
            cmd.execute()

        command_bus.dispatch.assert_not_called()

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_propagates_command_bus_failure(self, input_mock: MagicMock, getpass_mock: MagicMock) -> None:
        cmd, command_bus = self.make_cmd(("admin2", "manager", "Admin Two"))
        input_mock.side_effect = ["", ""]
        getpass_mock.side_effect = ["TempPass123", "TempPass123"]
        expected = PermissionError("Missing permission: ADMIN_USER")
        command_bus.dispatch.side_effect = expected

        with self.assertRaises(PermissionError) as raised:
            cmd.execute()

        self.assertIs(raised.exception, expected)
        command_bus.dispatch.assert_called_once()

    def _assert_dispatched(
        self,
        command_bus: MagicMock,
        *,
        username: str,
        role: Role,
        name: str,
        email: str,
        phone_number: str,
        password: str,
    ) -> None:
        """Assert one registration dispatch with the expected command data."""
        command_bus.dispatch.assert_called_once()
        self.assertIs(command_bus.dispatch.call_args.kwargs["key"], REGISTER_USER)
        command = command_bus.dispatch.call_args.kwargs["command"]
        self.assertIsInstance(command, RegisterUserCommand)
        self.assertEqual(command.username, username)
        self.assertIs(command.role, role)
        self.assertEqual(command.name, name)
        self.assertEqual(command.email, email)
        self.assertEqual(command.phone_number, phone_number)
        self.assertEqual(command.password, password)


if __name__ == "__main__":
    unittest.main()
