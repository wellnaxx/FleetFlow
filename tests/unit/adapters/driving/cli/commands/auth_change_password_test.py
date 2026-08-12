"""Tests for the self-service password-change CLI command."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_change_password import AuthChangePassword


class AuthChangePasswordShould(unittest.TestCase):
    """Verify prompting, validation, delegation, and event draining."""

    def make_cmd(self, params: tuple[str, ...] = ()) -> AuthChangePassword:
        return AuthChangePassword(params, MagicMock(), MagicMock())

    def test_skips_heartbeat(self) -> None:
        self.assertTrue(AuthChangePassword.skips_heartbeat)

    def test_rejects_arguments_before_prompting(self) -> None:
        cmd = self.make_cmd(("alice",))

        with self.assertRaisesRegex(ValueError, "does not accept arguments"):
            cmd.execute()

        cmd.use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_rejects_mismatched_confirmation(self, getpass_mock: MagicMock) -> None:
        cmd = self.make_cmd()
        getpass_mock.side_effect = ["OldPass123", "NewPass123", "Mismatch"]

        with self.assertRaisesRegex(ValueError, "Passwords do not match"):
            cmd.execute()

        cmd.use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_delegates_and_drains_events(self, getpass_mock: MagicMock) -> None:
        cmd = self.make_cmd()
        getpass_mock.side_effect = ["OldPass123", "NewPass123", "NewPass123"]

        result = cmd.execute()

        self.assertEqual(result, "Password changed.")
        cmd.use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            current_password="OldPass123",
            new_password="NewPass123",
        )
        cmd._event_collector.drain.assert_called_once_with((cmd.use_case,))  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_propagates_use_case_error_after_drain(self, getpass_mock: MagicMock) -> None:
        cmd = self.make_cmd()
        getpass_mock.side_effect = ["OldPass123", "NewPass123", "NewPass123"]
        cmd.use_case.execute.side_effect = PermissionError("Unauthenticated")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            cmd.execute()

        cmd._event_collector.drain.assert_called_once_with((cmd.use_case,))  # type: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    unittest.main()
