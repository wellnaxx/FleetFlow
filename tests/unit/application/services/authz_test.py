import unittest
from datetime import datetime
from typing import Any
from unittest.mock import patch

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.services.authorization_service import (
    AuthorizationService,
    requires,
    requires_all,
)
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.domain.enums.auth import Permission, Role


def _user(role: Role) -> CurrentUserPrincipal:
    return CurrentUserPrincipal(
        user_id=1,
        username="test.user",
        name="Test User",
        email="test@example.com",
        phone_number="0400000000",
        role=role,
    )


EMPTY_ROLE_PERMISSIONS: dict[Role, set[Permission]] = {}
MANAGER_CAN_CREATE_PACKAGES: dict[Role, set[Permission]] = {Role.MANAGER: {Permission.PACKAGE_CREATE}}
MANAGER_NO_PERMISSIONS: dict[Role, set[Permission]] = {Role.MANAGER: set()}


def _resolve_route_revision(
    _target: Any,
    route_id: int,
    *,
    revision: int = 0,
) -> str:
    """Build a deterministic target id from decorated method arguments."""
    return f"{route_id}:{revision}"


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

            @requires(
                Permission.ROUTE_REMOVE,
                operation=AuthorizationOperation.ROUTE_REMOVE,
                target_resource_type=AuditResourceType.ROUTE,
                target_resource_id_resolver=None,
            )
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

            @requires(
                Permission.PACKAGE_CREATE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
            def action(self) -> str:  # pragma: no cover - name only used for metadata
                return "x"

        with self.assertRaises(PermissionError) as ctx1:
            Unauthenticated().action()
        self.assertIn("Unauthenticated", str(ctx1.exception))

        class WithAuthz:
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))

            @requires(
                Permission.PACKAGE_CREATE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
            def action(self) -> str:
                return "x"

        with (
            patch("src.application.services.authorization_service.ROLE_PERMISSIONS", MANAGER_NO_PERMISSIONS),
            self.assertRaises(PermissionError) as ctx2,
        ):
            WithAuthz().action()
        self.assertIn("Missing permission: PACKAGE_CREATE", str(ctx2.exception))

    def test_requires_records_denied_event_for_unauthenticated_event_recorder(self) -> None:
        occurred_at = datetime(2025, 1, 1, 12, 0)

        class Target(ApplicationEventRecorderMixin):
            def __init__(self) -> None:
                self.authz = AuthorizationService(None)
                self._clock = lambda: occurred_at
                self._pending_events = []

            @requires(
                Permission.PACKAGE_CREATE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
            def action(self) -> str:
                return "x"

        target = Target()

        with self.assertRaises(PermissionError):
            target.action()

        event = target.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.PACKAGE_CREATE)
        self.assertIs(event.target_resource_type, AuditResourceType.PACKAGE)
        self.assertIsNone(event.target_resource_id)
        self.assertEqual(event.required_permissions, (Permission.PACKAGE_CREATE,))
        self.assertEqual(event.occurred_at, occurred_at)

    def test_requires_records_denied_event_for_missing_permission(self) -> None:
        occurred_at = datetime(2025, 1, 1, 12, 0)

        class Target(ApplicationEventRecorderMixin):
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))
                self._clock = lambda: occurred_at
                self._pending_events = []

            @requires(
                Permission.PACKAGE_CREATE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
            def action(self) -> str:
                return "x"

        target = Target()

        with (
            patch("src.application.services.authorization_service.ROLE_PERMISSIONS", MANAGER_NO_PERMISSIONS),
            self.assertRaises(PermissionError),
        ):
            target.action()

        event = target.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.PACKAGE_CREATE)
        self.assertIs(event.target_resource_type, AuditResourceType.PACKAGE)
        self.assertIsNone(event.target_resource_id)
        self.assertEqual(event.required_permissions, (Permission.PACKAGE_CREATE,))
        self.assertEqual(event.occurred_at, occurred_at)

    def test_requires_resolves_and_normalizes_denied_target_id(self) -> None:
        class Target(ApplicationEventRecorderMixin):
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))
                self._pending_events = []

            @requires(
                Permission.ROUTE_REMOVE,
                operation=AuthorizationOperation.ROUTE_REMOVE,
                target_resource_type=AuditResourceType.ROUTE,
                target_resource_id_resolver=_resolve_route_revision,
            )
            def action(self, route_id: int, *, revision: int = 0) -> None:
                raise AssertionError(f"Denied action unexpectedly ran for {route_id}:{revision}.")

        target = Target()

        with (
            patch("src.application.services.authorization_service.ROLE_PERMISSIONS", MANAGER_NO_PERMISSIONS),
            self.assertRaisesRegex(PermissionError, "Missing permission: ROUTE_REMOVE"),
        ):
            target.action(42, revision=3)

        event = target.pending_events[0]
        assert isinstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.ROUTE_REMOVE)
        self.assertIs(event.target_resource_type, AuditResourceType.ROUTE)
        self.assertEqual(event.target_resource_id, "42:3")

    def test_requires_all_allows_when_all_present(self) -> None:
        needed = {Permission.PACKAGE_CREATE, Permission.ROUTE_REMOVE}

        class OK:
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))

            @requires_all(
                Permission.PACKAGE_CREATE,
                Permission.ROUTE_REMOVE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
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

            @requires_all(
                Permission.PACKAGE_CREATE,
                Permission.ROUTE_REMOVE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
            def go(self) -> int:
                return 1

        with self.assertRaises(PermissionError) as ctx:
            Unauthenticated().go()
        self.assertIn("Unauthenticated", str(ctx.exception))

        class MissingOne:
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))

            @requires_all(
                Permission.PACKAGE_CREATE,
                Permission.ROUTE_REMOVE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
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

    def test_requires_all_records_only_missing_permissions(self) -> None:
        occurred_at = datetime(2025, 1, 1, 12, 0)

        class Target(ApplicationEventRecorderMixin):
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))
                self._clock = lambda: occurred_at
                self._pending_events = []

            @requires_all(
                Permission.PACKAGE_CREATE,
                Permission.ROUTE_REMOVE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
            def go(self) -> int:
                return 1

        target = Target()

        with (
            patch(
                "src.application.services.authorization_service.ROLE_PERMISSIONS",
                MANAGER_CAN_CREATE_PACKAGES,
            ),
            self.assertRaises(PermissionError),
        ):
            target.go()

        event = target.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.PACKAGE_CREATE)
        self.assertIs(event.target_resource_type, AuditResourceType.PACKAGE)
        self.assertIsNone(event.target_resource_id)
        self.assertEqual(event.required_permissions, (Permission.ROUTE_REMOVE,))
        self.assertEqual(event.occurred_at, occurred_at)

    def test_requires_all_records_all_required_permissions_when_unauthenticated(self) -> None:
        occurred_at = datetime(2025, 1, 1, 12, 0)

        class Target(ApplicationEventRecorderMixin):
            def __init__(self) -> None:
                self.authz = AuthorizationService(None)
                self._clock = lambda: occurred_at
                self._pending_events = []

            @requires_all(
                Permission.PACKAGE_CREATE,
                Permission.ROUTE_REMOVE,
                operation=AuthorizationOperation.PACKAGE_CREATE,
                target_resource_type=AuditResourceType.PACKAGE,
                target_resource_id_resolver=None,
            )
            def go(self) -> int:
                return 1

        target = Target()

        with self.assertRaises(PermissionError):
            target.go()

        event = target.pending_events[0]
        self.assertIsInstance(event, AuthorizationDenied)
        assert isinstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.PACKAGE_CREATE)
        self.assertIs(event.target_resource_type, AuditResourceType.PACKAGE)
        self.assertIsNone(event.target_resource_id)
        self.assertEqual(
            event.required_permissions,
            (Permission.PACKAGE_CREATE, Permission.ROUTE_REMOVE),
        )
        self.assertEqual(event.occurred_at, occurred_at)

    def test_requires_all_resolves_target_and_records_only_missing_permissions(self) -> None:
        class Target(ApplicationEventRecorderMixin):
            def __init__(self) -> None:
                self.authz = AuthorizationService(_user(Role.MANAGER))
                self._pending_events = []

            @requires_all(
                Permission.PACKAGE_CREATE,
                Permission.ROUTE_REMOVE,
                operation=AuthorizationOperation.ROUTE_REMOVE,
                target_resource_type=AuditResourceType.ROUTE,
                target_resource_id_resolver=_resolve_route_revision,
            )
            def action(self, route_id: int, *, revision: int = 0) -> None:
                raise AssertionError(f"Denied action unexpectedly ran for {route_id}:{revision}.")

        target = Target()

        with (
            patch(
                "src.application.services.authorization_service.ROLE_PERMISSIONS",
                MANAGER_CAN_CREATE_PACKAGES,
            ),
            self.assertRaisesRegex(PermissionError, "Missing permissions: ROUTE_REMOVE"),
        ):
            target.action(7, revision=2)

        event = target.pending_events[0]
        assert isinstance(event, AuthorizationDenied)
        self.assertEqual(event.target_resource_id, "7:2")
        self.assertEqual(event.required_permissions, (Permission.ROUTE_REMOVE,))
