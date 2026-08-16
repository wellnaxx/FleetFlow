"""Tests for the query-bus-backed WhoAmI CLI command."""

import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.auth_whoami import AuthWhoAmI
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.queries.auth.who_am_i import WHO_AM_I, WhoAmIQuery
from src.domain.enums.auth import Role
from src.ports.input.query_bus import QueryBus


class AuthWhoAmIShould(unittest.TestCase):
    """Verify query dispatch and CLI rendering for authentication context."""

    def make_cmd(self, params: tuple[str, ...] = ()) -> tuple[AuthWhoAmI, MagicMock]:
        """Return a command with an isolated query-bus mock."""
        query_bus = MagicMock(spec=QueryBus)
        return AuthWhoAmI(params, query_bus), query_bus

    def test_whoami_skips_heartbeat(self) -> None:
        self.assertTrue(AuthWhoAmI.skips_heartbeat)

    def test_not_logged_in_returns_message(self) -> None:
        cmd, query_bus = self.make_cmd()
        query_bus.dispatch.return_value = None

        result = cmd.execute()

        self.assertEqual(result, "Not logged in.")
        query_bus.dispatch.assert_called_once_with(key=WHO_AM_I, query=WhoAmIQuery())

    def test_logged_in_formats_name_and_role_value(self) -> None:
        cmd, query_bus = self.make_cmd()
        query_bus.dispatch.return_value = CurrentUserPrincipal(
            user_id=1,
            username="alice",
            name="Alice",
            email="",
            phone_number="",
            role=Role.MANAGER,
        )

        result = cmd.execute()

        self.assertEqual(result, "Alice [MANAGER]")
        query_bus.dispatch.assert_called_once_with(key=WHO_AM_I, query=WhoAmIQuery())

    def test_ignores_params_if_present(self) -> None:
        cmd, query_bus = self.make_cmd(("ignored", "stuff"))
        query_bus.dispatch.return_value = CurrentUserPrincipal(
            user_id=2,
            username="bob",
            name="Bob",
            email="",
            phone_number="",
            role=Role.EMPLOYEE,
        )

        result = cmd.execute()

        self.assertEqual(result, "Bob [EMPLOYEE]")

    def test_does_not_mutate_session(self) -> None:
        self.assertFalse(getattr(AuthWhoAmI, "mutates_session", False))


if __name__ == "__main__":
    unittest.main()
