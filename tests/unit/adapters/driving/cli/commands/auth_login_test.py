import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_login import AuthLogin


class AuthLogin_Should(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> AuthLogin:
        cmd = AuthLogin.__new__(AuthLogin)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def login_result(self, *, name: str, role: str) -> SimpleNamespace:
        return SimpleNamespace(user=SimpleNamespace(name=name, role=SimpleNamespace(value=role)))

    def test_mutates_session_true(self) -> None:
        self.assertTrue(AuthLogin.mutates_session)

    def test_login_skips_heartbeat(self) -> None:
        self.assertTrue(AuthLogin.skips_heartbeat)

    @patch("getpass.getpass")
    def test_execute_with_params_success(self, mock_getpass: MagicMock) -> None:
        # Arrange
        cmd = self.make_cmd(params=["alice "])  # note trailing space; code does NOT strip this path
        mock_getpass.return_value = "secretPW"
        cmd._use_case.execute.return_value = self.login_result(name="Alice", role="ADMIN")  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        # Assert
        cmd._use_case.execute.assert_called_once_with("alice ", "secretPW")  # type: ignore[reportUnknownMemberType]
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
        cmd._use_case.execute.return_value = self.login_result(name="Bob", role="USER")  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        # Assert
        mock_input.assert_called_once_with("Username: ")
        mock_getpass.assert_called_once_with("Password: ")
        cmd._use_case.execute.assert_called_once_with("Bob", "pw123456")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Logged in as Bob [USER]")

    @patch("getpass.getpass")
    @patch("builtins.input")
    def test_execute_propagates_login_errors(self, mock_input: MagicMock, mock_getpass: MagicMock) -> None:
        # Arrange
        cmd = self.make_cmd(params=[])
        mock_input.return_value = "carol"
        mock_getpass.return_value = "wrong"
        cmd._use_case.execute.side_effect = ValueError("invalid credentials")  # type: ignore[reportAttributeAccessIssue]

        # Act / Assert
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("invalid credentials", str(ctx.exception))
        mock_input.assert_called_once_with("Username: ")
        mock_getpass.assert_called_once_with("Password: ")
        cmd._use_case.execute.assert_called_once_with("carol", "wrong")  # type: ignore[reportUnknownMemberType]

    @patch("getpass.getpass")
    def test_execute_always_prompts_for_password(self, mock_getpass: MagicMock) -> None:
        # Arrange
        cmd = self.make_cmd(params=["dave"])
        mock_getpass.return_value = "pw"
        cmd._use_case.execute.return_value = self.login_result(name="Dave", role="OP")  # type: ignore[reportAttributeAccessIssue]

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
        cmd._use_case.execute.return_value = self.login_result(name="", role="USER")  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        cmd._use_case.execute.assert_called_once_with("", "pw")  # type: ignore[reportUnknownMemberType]
