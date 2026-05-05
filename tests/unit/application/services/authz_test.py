import unittest
from typing import Any
from unittest.mock import patch

from src.application.services.authorization_service import AuthorizationService, requires, requires_all
from src.domain.entities.users.user import User
from src.domain.enums.auth import Permission, Role
from src.domain.value_objects.contact_info import ContactInfo


def _user(role: Role) -> User:
    return User(ContactInfo("Test User", "test@example.com", "0400000000"), role, 1)


EMPTY_ROLE_PERMISSIONS: dict[Role, set[Permission]] = {}
MANAGER_CAN_CREATE_PACKAGES: dict[Role, set[Permission]] = {Role.MANAGER: {Permission.PACKAGE_CREATE}}
MANAGER_NO_PERMISSIONS: dict[Role, set[Permission]] = {Role.MANAGER: set()}


class Authz_Should(unittest.TestCase):
    @patch(
        "src.application.services.authorization_service.ROLE_PERMISSIONS",
        MANAGER_CAN_CREATE_PACKAGES,
    )
    def test_has_true_when_user_role_allows_permission(self) -> None:
        user = _user(Role.MANAGER)
        svc = AuthorizationService(current_user=user)
        self.assertTrue(svc.has(Permission.PACKAGE_CREATE))

    @patch("src.application.services.authorization_service.ROLE_PERMISSIONS", EMPTY_ROLE_PERMISSIONS)
    def test_has_false_when_no_current_user_or_role_not_mapped(self) -> None:
        svc = AuthorizationService(current_user=None)
        self.assertFalse(svc.has(Permission.PACKAGE_CREATE))

        user = _user(Role.EMPLOYEE)  # not present in patched map
        svc2 = AuthorizationService(current_user=user)
        self.assertFalse(svc2.has(Permission.PACKAGE_CREATE))

    def test_requires_allows_and_forwards_args_kwargs(self) -> None:
        calls: dict[str, Any] = {}

        class Target:
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))

            @requires(Permission.ROUTE_REMOVE)
            def do_work(self, a: Any, b: int = 0, *, k: Any = None) -> str:
                calls["args"] = (a, b, k)
                return "ok"

        t = Target()
        out = t.do_work(5, b=7, k="x")
        self.assertEqual(out, "ok")
        self.assertEqual(calls["args"], (5, 7, "x"))
        # wraps() preserves metadata
        self.assertEqual(Target.do_work.__name__, "do_work")
        self.assertIn("do_work", Target.do_work.__qualname__)

    def test_requires_raises_with_missing_permission_or_no_authz(self) -> None:
        class Unauthenticated:
            def __init__(self) -> None:
                self.authz = AuthorizationService(None)

            @requires(Permission.PACKAGE_CREATE)
            def action(self) -> str:  # pragma: no cover - name only used for metadata
                return "x"

        with self.assertRaises(PermissionError) as ctx1:
            Unauthenticated().action()
        self.assertIn("Unauthenticated", str(ctx1.exception))

        class WithAuthz:
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))

            @requires(Permission.PACKAGE_CREATE)
            def action(self) -> str:
                return "x"

        with (
            patch("src.application.services.authorization_service.ROLE_PERMISSIONS", MANAGER_NO_PERMISSIONS),
            self.assertRaises(PermissionError) as ctx2,
        ):
            WithAuthz().action()
        self.assertIn("Missing permission: PACKAGE_CREATE", str(ctx2.exception))

    def test_requires_all_allows_when_all_present(self) -> None:
        needed = {Permission.PACKAGE_CREATE, Permission.ROUTE_REMOVE}

        class OK:
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))

            @requires_all(Permission.PACKAGE_CREATE, Permission.ROUTE_REMOVE)
            def go(self) -> int:
                return 42

        with patch("src.application.services.authorization_service.ROLE_PERMISSIONS", {Role.MANAGER: needed}):
            self.assertEqual(OK().go(), 42)
        # metadata preserved
        self.assertEqual(OK.go.__name__, "go")

    def test_requires_all_raises_when_missing_or_no_authz(self) -> None:
        class Unauthenticated:
            def __init__(self) -> None:
                self.authz = AuthorizationService(None)

            @requires_all(Permission.PACKAGE_CREATE, Permission.ROUTE_REMOVE)
            def go(self) -> int:
                return 1

        with self.assertRaises(PermissionError) as ctx:
            Unauthenticated().go()
        self.assertIn("Unauthenticated", str(ctx.exception))

        class MissingOne:
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))

            @requires_all(Permission.PACKAGE_CREATE, Permission.ROUTE_REMOVE)
            def go(self) -> int:
                return 1

        with (
            patch(
                "src.application.services.authorization_service.ROLE_PERMISSIONS",
                MANAGER_CAN_CREATE_PACKAGES,
            ),
            self.assertRaises(PermissionError) as ctx2,
        ):
            MissingOne().go()
        self.assertIn("Missing permissions: ROUTE_REMOVE", str(ctx2.exception))
