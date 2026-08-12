"""Tests for the administrative password-reset CLI command."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_reset_password import AuthResetPassword


class AuthResetPasswordShould(unittest.TestCase):
    """Verify target parsing, prompting, delegation, and event draining."""

    def make_cmd(self, params: tuple[str, ...]) -> AuthResetPassword:
        return AuthResetPassword(params, MagicMock(), MagicMock())

    def test_skips_heartbeat(self) -> None:
        self.assertTrue(AuthResetPassword.skips_heartbeat)

    def test_requires_exactly_one_username(self) -> None:
        for params in ((), ("alice", "extra")):
            with self.subTest(params=params):
                cmd = self.make_cmd(params)
                with self.assertRaisesRegex(ValueError, "Usage"):
                    cmd.execute()

    def test_rejects_blank_username(self) -> None:
        cmd = self.make_cmd(("   ",))

        with self.assertRaisesRegex(ValueError, "non-empty"):
            cmd.execute()

    @patch("src.adapters.driving.cli.commands.auth_reset_password.getpass.getpass")
    def test_rejects_mismatched_confirmation(self, getpass_mock: MagicMock) -> None:
        cmd = self.make_cmd(("alice",))
        getpass_mock.side_effect = ["NewPass123", "Mismatch"]

        with self.assertRaisesRegex(ValueError, "Passwords do not match"):
            cmd.execute()

        cmd.use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_reset_password.getpass.getpass")
    def test_normalizes_target_delegates_and_drains_events(self, getpass_mock: MagicMock) -> None:
        cmd = self.make_cmd(("  ALICE  ",))
        getpass_mock.side_effect = ["NewPass123", "NewPass123"]

        result = cmd.execute()

        self.assertEqual(result, "Password reset for 'alice'.")
        cmd.use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            username="alice",
            new_password="NewPass123",
        )
        cmd._event_collector.drain.assert_called_once_with((cmd.use_case,))  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_reset_password.getpass.getpass")
    def test_propagates_permission_error_and_drains_events(self, getpass_mock: MagicMock) -> None:
        cmd = self.make_cmd(("alice",))
        getpass_mock.side_effect = ["NewPass123", "NewPass123"]
        expected = PermissionError("Missing permission: ADMIN_USER")
        cmd.use_case.execute.side_effect = expected  # type: ignore[reportUnknownMemberType]

        with self.assertRaises(PermissionError) as raised:
            cmd.execute()

        self.assertIs(raised.exception, expected)
        cmd._event_collector.drain.assert_called_once_with((cmd.use_case,))  # type: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    unittest.main()
