import unittest
from unittest.mock import MagicMock

from src.commands.auth_logout import AuthLogout


class AuthLogout_Should(unittest.TestCase):
    def make_cmd(self):
        cmd = AuthLogout.__new__(AuthLogout)
        cmd._auth = MagicMock()
        cmd._params = []  # not used, but keep consistent with other commands
        return cmd

    def test_mutates_session_true(self):
        self.assertTrue(AuthLogout.mutates_session)

    def test_execute_calls_logout_and_returns_message(self):
        cmd = self.make_cmd()
        result = cmd.execute()
        cmd._auth.logout.assert_called_once_with()
        self.assertEqual(result, "Logged out.")

    def test_execute_propagates_errors_from_auth(self):
        cmd = self.make_cmd()
        cmd._auth.logout.side_effect = RuntimeError("session not found")

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("session not found", str(ctx.exception))
        cmd._auth.logout.assert_called_once_with()

    def test_execute_ignores_params_if_present(self):
        cmd = self.make_cmd()
        cmd._params = ["extra", "ignored"]
        result = cmd.execute()
        cmd._auth.logout.assert_called_once_with()
        self.assertEqual(result, "Logged out.")

