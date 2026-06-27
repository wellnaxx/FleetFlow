import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.auth_register import AuthRegisterUser
from src.domain.enums.auth import Role


class AuthRegisterUser_Should(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> AuthRegisterUser:
        cmd = AuthRegisterUser.__new__(AuthRegisterUser)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_register_skips_heartbeat(self) -> None:
        self.assertTrue(AuthRegisterUser.skips_heartbeat)

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_prompt_mode_success_all_fields(self, mock_input: MagicMock, mock_gp: MagicMock) -> None:
        # Arrange: missing all -> prompt for each
        cmd = self.make_cmd(params=[])
        # Username, Role, Name, Email, Phone
        mock_input.side_effect = [
            "  Alice  ",
            "  MANager ",
            " Alice Wonder ",
            "  alice@example.com ",
            "  0412345678  ",
        ]
        mock_gp.side_effect = ["TempPass123", "TempPass123"]

        # Mock return record from register_user
        rec = SimpleNamespace(username="alice", role=Role.MANAGER, user_id=101)
        cmd._use_case.execute.return_value = rec  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        # Assert: CLI trims display/contact fields, while username normalization
        # is enforced by the use case/auth service.
        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            username="  Alice  ",
            role=Role.MANAGER,
            name="Alice Wonder",
            email="alice@example.com",
            phone_number="0412345678",
            password="TempPass123",
        )
        self.assertEqual(result, f"Created {Role.MANAGER} user 'alice' (id=101).")

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    def test_hybrid_mode_success_with_all_params(self, mock_gp: MagicMock) -> None:
        # Arrange: username, role, name, email, phone provided
        cmd = self.make_cmd(params=["Bob", "employee", "Bob B.", "bob@ex.com", "0411222333"])
        mock_gp.side_effect = ["SuperStrong1", "SuperStrong1"]
        rec = SimpleNamespace(username="bob", role=Role.EMPLOYEE, user_id=202)
        cmd._use_case.execute.return_value = rec  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            username="Bob",
            role=Role.EMPLOYEE,
            name="Bob B.",
            email="bob@ex.com",
            phone_number="0411222333",
            password="SuperStrong1",
        )
        self.assertEqual(result, f"Created {Role.EMPLOYEE} user 'bob' (id=202).")

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_role_parsing_accepts_prefixes(self, mock_input: MagicMock, mock_gp: MagicMock) -> None:
        # Email/phone are missing -> patch input to avoid hang
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["carol", "MAN", "Carol C."])
        mock_gp.side_effect = ["Pa55word!!", "Pa55word!!"]
        cmd._use_case.execute.return_value = SimpleNamespace(  # type: ignore[reportAttributeAccessIssue]
            username="carol", role=Role.MANAGER, user_id=303
        )

        _ = cmd.execute()
        # Ensure manager was selected
        (_, kwargs) = cmd._use_case.execute.call_args  # type: ignore[reportAttributeAccessIssue]
        self.assertEqual(kwargs["role"], Role.MANAGER)

    @patch("builtins.input")
    def test_role_invalid_raises(self, mock_input: MagicMock) -> None:
        # Email/phone prompts occur before role validation, so patch input
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["dave", "lead", "Dave D."])
        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Role must be 'employee' or 'manager'", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_passwords_must_match(self, mock_input: MagicMock, mock_gp: MagicMock) -> None:
        # Email/phone missing -> patch input first
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["erin", "employee", "Erin E."])
        mock_gp.side_effect = ["Temp1234", "Mismatch1234"]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("Passwords do not match", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_password_min_length(self, mock_input: MagicMock, mock_gp: MagicMock) -> None:
        # Email/phone missing -> patch input first
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["frank", "employee", "Frank F."])
        mock_gp.side_effect = ["short7", "short7"]  # 7 chars
        cmd._use_case.execute.side_effect = ValueError("Password must be at least 8 characters.")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()
        self.assertIn("at least 8", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            username="frank",
            role=Role.EMPLOYEE,
            name="Frank F.",
            email="",
            phone_number="",
            password="short7",
        )

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_missing_optional_fields_are_empty_when_skipped(
        self, mock_input: MagicMock, mock_gp: MagicMock
    ) -> None:
        cmd = self.make_cmd(params=[" Gina ", " Emp ", "  Gina G  "])  # email/phone missing
        mock_input.side_effect = ["", ""]  # email, phone prompts -> empty
        mock_gp.side_effect = ["PassWord999", "PassWord999"]
        rec = SimpleNamespace(username="gina", role=Role.EMPLOYEE, user_id=404)
        cmd._use_case.execute.return_value = rec  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            username=" Gina ",
            role=Role.EMPLOYEE,
            name="Gina G",
            email="",
            phone_number="",
            password="PassWord999",
        )
        self.assertEqual(result, f"Created {Role.EMPLOYEE} user 'gina' (id=404).")

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_register_user_errors_propagate(self, mock_input: MagicMock, mock_gp: MagicMock) -> None:
        # Email/phone missing -> patch input
        mock_input.side_effect = ["", ""]
        cmd = self.make_cmd(params=["harry", "manager", "Harry H."])
        mock_gp.side_effect = ["CorrectHorse1", "CorrectHorse1"]
        cmd._use_case.execute.side_effect = PermissionError("not allowed")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("not allowed", str(ctx.exception))

    @patch("src.adapters.driving.cli.commands.auth_register.getpass.getpass")
    @patch("builtins.input")
    def test_permission_errors_from_use_case_propagate(self, mock_input: MagicMock, mock_gp: MagicMock) -> None:
        mock_input.side_effect = ["", ""]
        mock_gp.side_effect = ["TempPass123", "TempPass123"]
        cmd = self.make_cmd(params=["admin2", "manager", "Admin Two"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ADMIN_USER")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ADMIN_USER", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            username="admin2",
            role=Role.MANAGER,
            name="Admin Two",
            email="",
            phone_number="",
            password="TempPass123",
        )

    def test_no_mutates_session_flag_present(self) -> None:
        self.assertFalse(getattr(AuthRegisterUser, "mutates_session", False))
