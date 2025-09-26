import unittest
from unittest.mock import patch, MagicMock

from src.commands.auth_change_password import AuthChangePassword
from src.models.auth import Permission


class AuthChangePassword_Should(unittest.TestCase):
    def make_cmd(self, params=None):
        cmd = AuthChangePassword.__new__(AuthChangePassword)
        cmd._params = params or []
        # stub app_data.authz and auth
        cmd._app_data = MagicMock()
        cmd._app_data.authz = MagicMock()
        cmd._auth = MagicMock()
        return cmd


    @patch('src.commands.auth_change_password.getpass.getpass')
    def test_manager_success_resets_password_and_lowercases_target(self, mock_gp):
        # Arrange
        cmd = self.make_cmd(params=["  Alice  "])
        cmd._app_data.authz.has.return_value = True
        # Simulate new/confirm prompts
        mock_gp.side_effect = ["SuperGood123", "SuperGood123"]

        # Act
        result = cmd.execute()

        # Assert
        cmd._app_data.authz.has.assert_called_once_with(Permission.ADMIN_USER)
        cmd._auth.reset_password.assert_called_once_with("alice", "SuperGood123")
        self.assertEqual(result, "Password reset for 'alice'.")

    @patch('src.commands.auth_change_password.getpass.getpass')
    def test_manager_missing_permission_raises_and_does_not_call_reset(self, mock_gp):
        cmd = self.make_cmd(params=["bob"])
        cmd._app_data.authz.has.return_value = False

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("Missing permission: ADMIN_USER", str(ctx.exception))
        cmd._auth.reset_password.assert_not_called()
        mock_gp.assert_not_called()

    @patch('src.commands.auth_change_password.getpass.getpass')
    def test_manager_mismatched_passwords_raises(self, mock_gp):
        cmd = self.make_cmd(params=["carol"])
        cmd._app_data.authz.has.return_value = True
        mock_gp.side_effect = ["NewPass123", "Different!"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Passwords do not match", str(ctx.exception))
        cmd._auth.reset_password.assert_not_called()

    @patch('src.commands.auth_change_password.getpass.getpass')
    def test_manager_too_short_password_raises(self, mock_gp):
        cmd = self.make_cmd(params=["dave"])
        cmd._app_data.authz.has.return_value = True
        mock_gp.side_effect = ["short", "short"]  # < 8 chars

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("at least 8", str(ctx.exception))
        cmd._auth.reset_password.assert_not_called()


    def test_selfservice_requires_login(self):
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = None  # not logged in

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("Not logged in", str(ctx.exception))

    def test_selfservice_requires_last_username(self):
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()
        cmd._auth.last_username = None

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()
        self.assertIn("No login username recorded", str(ctx.exception))

    @patch('src.commands.auth_change_password.getpass.getpass')
    def test_selfservice_mismatched_passwords_raises(self, mock_gp):
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()
        cmd._auth.last_username = "erin"
        mock_gp.side_effect = ["OldPass123", "NewPass123", "Mismatch"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Passwords do not match", str(ctx.exception))
        cmd._auth.change_password.assert_not_called()

    @patch('src.commands.auth_change_password.getpass.getpass')
    def test_selfservice_too_short_password_raises(self, mock_gp):
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()
        cmd._auth.last_username = "frank"
        mock_gp.side_effect = ["OldPass123", "short", "short"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("at least 8", str(ctx.exception))
        cmd._auth.change_password.assert_not_called()

    @patch('src.commands.auth_change_password.getpass.getpass')
    def test_selfservice_new_same_as_old_raises(self, mock_gp):
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()
        cmd._auth.last_username = "grace"
        mock_gp.side_effect = ["SamePass123", "SamePass123", "SamePass123"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("must be different", str(ctx.exception))
        cmd._auth.change_password.assert_not_called()

    @patch('src.commands.auth_change_password.getpass.getpass')
    def test_selfservice_success_calls_change_password(self, mock_gp):
        cmd = self.make_cmd(params=[])
        cmd._auth.current_user = MagicMock()
        cmd._auth.last_username = "henry"
        mock_gp.side_effect = ["OldPass123", "BrandNew123", "BrandNew123"]

        result = cmd.execute()

        cmd._auth.change_password.assert_called_once_with("henry", "OldPass123", "BrandNew123")
        self.assertEqual(result, "Password changed.")


if __name__ == "__main__":
    unittest.main()
