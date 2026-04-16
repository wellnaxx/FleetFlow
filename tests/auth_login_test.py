import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from adapters.driving.cli.commands.auth_login import AuthLogin


class AuthLogin_Should(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> AuthLogin:
        cmd = AuthLogin.__new__(AuthLogin)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._auth = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_mutates_session_true(self) -> None:
        self.assertTrue(AuthLogin.mutates_session)

    @patch("getpass.getpass")
    def test_execute_with_params_success(self, mock_getpass: MagicMock) -> None:
        # Arrange
        cmd = self.make_cmd(params=["alice "])  # note trailing space; code does NOT strip this path
        mock_getpass.return_value = "secretPW"
        user_obj = SimpleNamespace(name="Alice", role=SimpleNamespace(value="ADMIN"))
        cmd._auth.login.return_value = user_obj  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        # Assert
        cmd._auth.login.assert_called_once_with("alice ", "secretPW")  # type: ignore[reportUnknownMemberType]
        mock_getpass.assert_called_once_with("Password: ")
        self.assertEqual(result, "Logged in as Alice [ADMIN]")

    @patch("getpass.getpass")
    @patch("builtins.input")
    def test_execute_prompts_for_username_and_strips_it(
        self, mock_input: MagicMock, mock_getpass: MagicMock
    ) -> None:
        # Arrange
        cmd = self.make_cmd(params=[])  # triggers prompt path
        mock_input.return_value = "  Bob\t"
        mock_getpass.return_value = "pw123456"
        user_obj = SimpleNamespace(name="Bob", role=SimpleNamespace(value="USER"))
        cmd._auth.login.return_value = user_obj  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        # Assert
        mock_input.assert_called_once_with("Username: ")
        mock_getpass.assert_called_once_with("Password: ")
        cmd._auth.login.assert_called_once_with("Bob", "pw123456")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Logged in as Bob [USER]")

    @patch("getpass.getpass")
    @patch("builtins.input")
    def test_execute_propagates_login_errors(self, mock_input: MagicMock, mock_getpass: MagicMock) -> None:
        # Arrange
        cmd = self.make_cmd(params=[])
        mock_input.return_value = "carol"
        mock_getpass.return_value = "wrong"
        cmd._auth.login.side_effect = ValueError("invalid credentials")  # type: ignore[reportAttributeAccessIssue]

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("invalid credentials", str(ctx.exception))
        mock_input.assert_called_once_with("Username: ")
        mock_getpass.assert_called_once_with("Password: ")
        cmd._auth.login.assert_called_once_with("carol", "wrong")  # type: ignore[reportUnknownMemberType]

    @patch("getpass.getpass")
    def test_execute_always_prompts_for_password(self, mock_getpass: MagicMock) -> None:
        # Arrange
        cmd = self.make_cmd(params=["dave"])
        mock_getpass.return_value = "pw"
        cmd._auth.login.return_value = SimpleNamespace(name="Dave", role=SimpleNamespace(value="OP"))  # type: ignore[reportAttributeAccessIssue]

        # Act
        _ = cmd.execute()

        # Assert
        mock_getpass.assert_called_once_with("Password: ")

    @patch("getpass.getpass")
    def test_execute_passes_empty_username_if_given(self, mock_getpass: MagicMock) -> None:
        """
        If caller provides an empty username in params, the command forwards it as-is.
        (No stripping occurs on the params path.)
        """
        cmd = self.make_cmd(params=[""])
        mock_getpass.return_value = "pw"
        cmd._auth.login.return_value = SimpleNamespace(name="", role=SimpleNamespace(value="USER"))  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        cmd._auth.login.assert_called_once_with("", "pw")  # type: ignore[reportUnknownMemberType]
