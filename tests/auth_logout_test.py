from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.commands.auth_logout import AuthLogout


class AuthLogout_Should(unittest.TestCase):
    def make_cmd(self) -> AuthLogout:
        cmd = AuthLogout.__new__(AuthLogout)
        cmd._auth = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._params = []  # type: ignore[reportAttributeAccessIssue]  # not used, but keep consistent with other commands
        return cmd

    def test_mutates_session_true(self) -> None:
        self.assertTrue(AuthLogout.mutates_session)

    def test_execute_calls_logout_and_returns_message(self) -> None:
        cmd = self.make_cmd()
        result = cmd.execute()
        cmd._auth.logout.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Logged out.")

    def test_execute_propagates_errors_from_auth(self) -> None:
        cmd = self.make_cmd()
        cmd._auth.logout.side_effect = RuntimeError("session not found")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("session not found", str(ctx.exception))
        cmd._auth.logout.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_execute_ignores_params_if_present(self) -> None:
        cmd = self.make_cmd()
        cmd._params = ["extra", "ignored"]  # type: ignore[reportAttributeAccessIssue]
        result = cmd.execute()
        cmd._auth.logout.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Logged out.")
