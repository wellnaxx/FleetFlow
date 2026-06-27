import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_change_password import AuthChangePassword


class AuthChangePassword_Should(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> AuthChangePassword:
        cmd = AuthChangePassword.__new__(AuthChangePassword)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case.current_session_username = "alice"  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_change_password_skips_heartbeat(self) -> None:
        self.assertTrue(AuthChangePassword.skips_heartbeat)

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_manager_success_resets_password_and_lowercases_target(self, mock_gp: MagicMock) -> None:
        # Arrange
        cmd = self.make_cmd(params=["  Alice  "])
        mock_gp.side_effect = ["SuperGood123", "SuperGood123"]

        result = cmd.execute()

        cmd._use_case.execute.assert_called_once_with("alice", "SuperGood123")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Password reset for 'alice'.")

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_manager_permission_errors_from_use_case_propagate(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=["bob"])
        mock_gp.side_effect = ["SuperGood123", "SuperGood123"]
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ADMIN_USER")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("Missing permission: ADMIN_USER", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with("bob", "SuperGood123")  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_manager_mismatched_passwords_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=["carol"])
        mock_gp.side_effect = ["NewPass123", "Different!"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Passwords do not match", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_manager_too_short_password_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=["dave"])
        mock_gp.side_effect = ["short", "short"]  # < 8 chars
        cmd._use_case.execute.side_effect = ValueError("Password must be at least 8 characters.")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("at least 8", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with("dave", "short")  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_permission_errors_from_use_case_propagate(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        mock_gp.side_effect = ["OldPass123", "BrandNew123", "BrandNew123"]
        cmd._use_case.execute_current_user.side_effect = PermissionError("Unauthenticated")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("Unauthenticated", str(ctx.exception))
        cmd._use_case.execute_current_user.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            "alice",
            "BrandNew123",
            old_password="OldPass123",
        )

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_session_errors_from_use_case_propagate(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        mock_gp.side_effect = ["OldPass123", "BrandNew123", "BrandNew123"]
        cmd._use_case.current_session_username = None  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case.execute_current_user.side_effect = PermissionError(  # type: ignore[reportAttributeAccessIssue]
            "Authenticated user has no username."
        )

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("no username", str(ctx.exception))
        cmd._use_case.execute_current_user.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            None,
            "BrandNew123",
            old_password="OldPass123",
        )

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_mismatched_passwords_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        mock_gp.side_effect = ["OldPass123", "NewPass123", "Mismatch"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Passwords do not match", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_too_short_password_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        mock_gp.side_effect = ["OldPass123", "short", "short"]
        cmd._use_case.execute_current_user.side_effect = ValueError("Password must be at least 8 characters.")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("at least 8", str(ctx.exception))
        cmd._use_case.execute_current_user.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            "alice",
            "short",
            old_password="OldPass123",
        )

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_new_same_as_old_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        mock_gp.side_effect = ["SamePass123", "SamePass123", "SamePass123"]
        cmd._use_case.execute_current_user.side_effect = ValueError(  # type: ignore[reportAttributeAccessIssue]
            "New password must be different from the old one."
        )

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("must be different", str(ctx.exception))
        cmd._use_case.execute_current_user.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            "alice",
            "SamePass123",
            old_password="SamePass123",
        )

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_success_calls_change_password(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        mock_gp.side_effect = ["OldPass123", "BrandNew123", "BrandNew123"]

        result = cmd.execute()

        cmd._use_case.execute_current_user.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            "alice",
            "BrandNew123",
            old_password="OldPass123",
        )
        self.assertEqual(result, "Password changed.")


if __name__ == "__main__":
    unittest.main()
