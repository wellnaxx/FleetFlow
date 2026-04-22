import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.auth_whoami import AuthWhoAmI


class AuthWhoAmI_Tests(unittest.TestCase):
    def make_cmd(self):
        cmd = AuthWhoAmI.__new__(AuthWhoAmI)
        cmd._use_case = MagicMock()  # type: ignore[reportPrivateUsage]
        cmd._params = []  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_not_logged_in_returns_message(self):
        cmd = self.make_cmd()
        cmd._use_case.execute.return_value = None  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "Not logged in.")

    def test_logged_in_formats_name_and_role_value(self):
        cmd = self.make_cmd()
        cmd._use_case.execute.return_value = SimpleNamespace(  # type: ignore[reportAttributeAccessIssue]
            name="Alice", role=SimpleNamespace(value="ADMIN")
        )

        result = cmd.execute()

        self.assertEqual(result, "Alice [ADMIN]")

    def test_ignores_params_if_present(self):
        cmd = self.make_cmd()
        cmd._params = ["ignored", "stuff"]  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case.execute.return_value = SimpleNamespace(  # type: ignore[reportAttributeAccessIssue]
            name="Bob", role=SimpleNamespace(value="USER")
        )

        result = cmd.execute()

        self.assertEqual(result, "Bob [USER]")

    def test_no_mutates_session_flag(self):
        # The command should not declare mutates_session
        self.assertFalse(getattr(AuthWhoAmI, "mutates_session", False))
