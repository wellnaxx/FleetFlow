import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from src.commands.auth_register import AuthRegisterUser
from src.models.auth import Role


class AuthRegisterUser_Should(unittest.TestCase):
    def make_cmd(self, params=None):
        cmd = AuthRegisterUser.__new__(AuthRegisterUser)
        cmd._params = params or []
        cmd._app_data = MagicMock()
        cmd._auth = MagicMock()
        return cmd


    @patch('src.commands.auth_register.getpass.getpass')
    @patch('builtins.input')
    def test_prompt_mode_success_all_fields(self, mock_input, mock_gp):
        # Arrange: missing all -> prompt for each
        cmd = self.make_cmd(params=[])
        # Username, Role, Name, Email, Phone
        mock_input.side_effect = [
            "  Alice  ", "  MANager ", " Alice Wonder ",
            "  alice@example.com ", "  0412345678  "
        ]
        mock_gp.side_effect = ["TempPass123", "TempPass123"]

        # Mock return record from register_user
        rec = SimpleNamespace(username="alice", role=Role.MANAGER, user_id=101)
        cmd._app_data.register_user.return_value = rec

        # Act
        result = cmd.execute()

        # Assert: inputs were stripped/lowercased as specified
        cmd._app_data.register_user.assert_called_once_with(
            username="alice",
            role=Role.MANAGER,
            name="Alice Wonder",
            email="alice@example.com",
            phone="0412345678",
            password="TempPass123",
            auth_service=cmd._auth
        )
        self.assertEqual(result, f"Created {Role.MANAGER} user 'alice' (id=101).")

    @patch('src.commands.auth_register.getpass.getpass')
    def test_hybrid_mode_success_with_all_params(self, mock_gp):
        # Arrange: username, role, name, email, phone provided
        cmd = self.make_cmd(params=["Bob", "employee", "Bob B.", "bob@ex.com", "0411222333"])
        mock_gp.side_effect = ["SuperStrong1", "SuperStrong1"]
        rec = SimpleNamespace(username="bob", role=Role.EMPLOYEE, user_id=202)
        cmd._app_data.register_user.return_value = rec

        # Act
        result = cmd.execute()

        # Assert: username is lowercased, role parsed from 'employee'
        cmd._app_data.register_user.assert_called_once_with(
            username="bob",
            role=Role.EMPLOYEE,
            name="Bob B.",
            email="bob@ex.com",
            phone="0411222333",
            password="SuperStrong1",
            auth_service=cmd._auth
        )
        self.assertEqual(result, f"Created {Role.EMPLOYEE} user 'bob' (id=202).")


    @patch('src.commands.auth_register.getpass.getpass')
    @patch('builtins.input')
    def test_role_parsing_accepts_prefixes(self, mock_input, mock_gp):
        # Email/phone are missing -> patch input to avoid hang
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["carol", "MAN", "Carol C."])
        mock_gp.side_effect = ["Pa55word!!", "Pa55word!!"]
        cmd._app_data.register_user.return_value = SimpleNamespace(
            username="carol", role=Role.MANAGER, user_id=303
        )

        _ = cmd.execute()
        # Ensure manager was selected
        (_, kwargs) = cmd._app_data.register_user.call_args
        self.assertEqual(kwargs["role"], Role.MANAGER)

    @patch('builtins.input')
    def test_role_invalid_raises(self, mock_input):
        # Email/phone prompts occur before role validation, so patch input
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["dave", "lead", "Dave D."])
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Role must be 'employee' or 'manager'", str(ctx.exception))
        cmd._app_data.register_user.assert_not_called()


    @patch('src.commands.auth_register.getpass.getpass')
    @patch('builtins.input')
    def test_passwords_must_match(self, mock_input, mock_gp):
        # Email/phone missing -> patch input first
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["erin", "employee", "Erin E."])
        mock_gp.side_effect = ["Temp1234", "Mismatch1234"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Passwords do not match", str(ctx.exception))
        cmd._app_data.register_user.assert_not_called()

    @patch('src.commands.auth_register.getpass.getpass')
    @patch('builtins.input')
    def test_password_min_length(self, mock_input, mock_gp):
        # Email/phone missing -> patch input first
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["frank", "employee", "Frank F."])
        mock_gp.side_effect = ["short7", "short7"]  # 7 chars

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("at least 8", str(ctx.exception))
        cmd._app_data.register_user.assert_not_called()


    @patch('src.commands.auth_register.getpass.getpass')
    @patch('builtins.input')
    def test_missing_optional_fields_are_empty_when_skipped(self, mock_input, mock_gp):
        cmd = self.make_cmd(params=[" Gina ", " Emp ", "  Gina G  "])  # email/phone missing
        mock_input.side_effect = ["", ""]  # email, phone prompts -> empty
        mock_gp.side_effect = ["PassWord999", "PassWord999"]
        rec = SimpleNamespace(username="gina", role=Role.EMPLOYEE, user_id=404)
        cmd._app_data.register_user.return_value = rec

        result = cmd.execute()

        cmd._app_data.register_user.assert_called_once_with(
            username="gina",
            role=Role.EMPLOYEE,
            name="Gina G",
            email="",
            phone="",
            password="PassWord999",
            auth_service=cmd._auth
        )
        self.assertEqual(result, f"Created {Role.EMPLOYEE} user 'gina' (id=404).")


    @patch('src.commands.auth_register.getpass.getpass')
    @patch('builtins.input')
    def test_register_user_errors_propagate(self, mock_input, mock_gp):
        # Email/phone missing -> patch input
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["harry", "manager", "Harry H."])
        mock_gp.side_effect = ["CorrectHorse1", "CorrectHorse1"]
        cmd._app_data.register_user.side_effect = PermissionError("not allowed")

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("not allowed", str(ctx.exception))


    def test_no_mutates_session_flag_present(self):
        self.assertFalse(getattr(AuthRegisterUser, "mutates_session", False))

