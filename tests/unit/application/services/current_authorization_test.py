"""Tests for context-local authorization identity."""

import asyncio
import unittest

from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.services.authorization_service import AuthorizationService
from src.application.services.current_authorization import (
    bind_authorization_context,
    get_authorization_context,
    get_optional_authorization_context,
)
from src.domain.enums.auth import Permission, Role


def principal(user_id: int, role: Role) -> CurrentUserPrincipal:
    """Build a deterministic authorization principal."""
    return CurrentUserPrincipal(
        user_id=user_id,
        username=f"user{user_id}",
        name=f"User {user_id}",
        email="",
        phone_number="",
        role=role,
    )


class CurrentAuthorizationShould(unittest.IsolatedAsyncioTestCase):
    """Verify binding, restoration, and service principal resolution."""

    def test_require_context_when_unbound_and_offer_optional_lookup(self) -> None:
        self.assertIsNone(get_optional_authorization_context())

        with self.assertRaisesRegex(RuntimeError, "No authorization context is bound"):
            get_authorization_context()

    def test_bind_principal_and_restore_unbound_state(self) -> None:
        user = principal(1, Role.MANAGER)

        with bind_authorization_context(user) as context:
            self.assertIs(get_authorization_context(), context)
            self.assertIs(context.current_user, user)

        self.assertIsNone(get_optional_authorization_context())

    def test_distinguish_explicit_unauthenticated_context_from_no_context(self) -> None:
        fallback = principal(1, Role.MANAGER)
        authorization = AuthorizationService(fallback)

        with bind_authorization_context(None) as context:
            self.assertIsNone(context.current_user)
            self.assertIsNone(authorization.current_user)
            self.assertFalse(authorization.has(Permission.AUDIT_VIEW))

        self.assertIs(authorization.current_user, fallback)

    def test_nested_binding_restore_outer_principal_after_inner_failure(self) -> None:
        outer_user = principal(1, Role.MANAGER)
        inner_user = principal(2, Role.EMPLOYEE)

        with bind_authorization_context(outer_user) as outer:
            with (
                self.assertRaisesRegex(RuntimeError, "inner failed"),
                bind_authorization_context(inner_user),
            ):
                self.assertIs(get_authorization_context().current_user, inner_user)
                raise RuntimeError("inner failed")

            self.assertIs(get_authorization_context(), outer)
            self.assertIs(get_authorization_context().current_user, outer_user)

        self.assertIsNone(get_optional_authorization_context())

    def test_authorization_service_prefer_scoped_user_then_restore_session_fallback(self) -> None:
        session_user = principal(1, Role.EMPLOYEE)
        request_user = principal(2, Role.MANAGER)
        authorization = AuthorizationService(session_user)

        with bind_authorization_context(request_user):
            self.assertIs(authorization.current_user, request_user)
            self.assertTrue(authorization.has(Permission.AUDIT_VIEW))

        self.assertIs(authorization.current_user, session_user)
        self.assertFalse(authorization.has(Permission.AUDIT_VIEW))

        replacement = principal(3, Role.MANAGER)
        authorization.current_user = replacement
        self.assertIs(authorization.current_user, replacement)

    async def test_isolate_principals_between_concurrent_tasks(self) -> None:
        first = principal(1, Role.MANAGER)
        second = principal(2, Role.EMPLOYEE)

        async def observe(user: CurrentUserPrincipal) -> CurrentUserPrincipal | None:
            with bind_authorization_context(user):
                await asyncio.sleep(0)
                return get_authorization_context().current_user

        first_result, second_result = await asyncio.gather(observe(first), observe(second))

        self.assertIs(first_result, first)
        self.assertIs(second_result, second)
        self.assertIsNone(get_optional_authorization_context())


if __name__ == "__main__":
    unittest.main()
