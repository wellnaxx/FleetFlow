import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_change_password import AuthChangePassword
from src.domain.enums.auth import Permission


class AuthChangePassword_Should(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> AuthChangePassword:
        cmd = AuthChangePassword.__new__(AuthChangePassword)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        # stub app_data.authz and auth
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data.authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._auth = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_manager_success_resets_password_and_lowercases_target(self, mock_gp: MagicMock) -> None:
        # Arrange
        cmd = self.make_cmd(params=["  Alice  "])
        cmd._app_data.authz.has.return_value = True  # type: ignore[reportAttributeAccessIssue]
        # Simulate new/confirm prompts
        mock_gp.side_effect = ["SuperGood123", "SuperGood123"]

        # Act
        result = cmd.execute()

        # Assert
        cmd._app_data.authz.has.assert_called_once_with(Permission.ADMIN_USER)  # type: ignore[reportUnknownMemberType]
        cmd._use_case.execute.assert_called_once_with("alice", "SuperGood123")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Password reset for 'alice'.")

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_manager_missing_permission_raises_and_does_not_call_reset(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=["bob"])
        cmd._app_data.authz.has.return_value = False  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("Missing permission: ADMIN_USER", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]
        mock_gp.assert_not_called()

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_manager_mismatched_passwords_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=["carol"])
        cmd._app_data.authz.has.return_value = True  # type: ignore[reportAttributeAccessIssue]
        mock_gp.side_effect = ["NewPass123", "Different!"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Passwords do not match", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_manager_too_short_password_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=["dave"])
        cmd._app_data.authz.has.return_value = True  # type: ignore[reportAttributeAccessIssue]
        mock_gp.side_effect = ["short", "short"]  # < 8 chars

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("at least 8", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    def test_selfservice_requires_login(self) -> None:
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = None  # type: ignore[reportAttributeAccessIssue]  # not logged in

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("Not logged in", str(ctx.exception))

    def test_selfservice_requires_last_username(self) -> None:
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._auth.last_username = None  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()
        self.assertIn("No login username recorded", str(ctx.exception))

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_mismatched_passwords_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._auth.last_username = "erin"  # type: ignore[reportAttributeAccessIssue]
        mock_gp.side_effect = ["OldPass123", "NewPass123", "Mismatch"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Passwords do not match", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_too_short_password_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._auth.last_username = "frank"  # type: ignore[reportAttributeAccessIssue]
        mock_gp.side_effect = ["OldPass123", "short", "short"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("at least 8", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_new_same_as_old_raises(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._auth.last_username = "grace"  # type: ignore[reportAttributeAccessIssue]
        mock_gp.side_effect = ["SamePass123", "SamePass123", "SamePass123"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("must be different", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_change_password.getpass.getpass")
    def test_selfservice_success_calls_change_password(self, mock_gp: MagicMock) -> None:
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._auth.last_username = "henry"  # type: ignore[reportAttributeAccessIssue]
        mock_gp.side_effect = ["OldPass123", "BrandNew123", "BrandNew123"]

        result = cmd.execute()

        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            "henry",
            "BrandNew123",
            old_password="OldPass123",
        )
        self.assertEqual(result, "Password changed.")


if __name__ == "__main__":
    unittest.main()
