"""Permission checks and decorators for command authorization."""

from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Concatenate, Protocol, overload

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.domain.enums.auth import ROLE_PERMISSIONS, Permission


class AuthorizationService:
    """Tracks current user and exposes permission checks."""

    def __init__(self, current_user: CurrentUserPrincipal | None) -> None:
        """Initialize authorization state.

        Args:
            current_user: Current authenticated principal, or `None` when unauthenticated.
        """
        self.current_user: CurrentUserPrincipal | None = current_user

    def has(self, perm: Permission) -> bool:
        """Return whether the current user has a permission.

        Args:
            perm: Permission to check.

        Returns:
            True when a current user exists and their role grants the permission.
        """
        if not self.current_user:
            return False
        allowed: frozenset[Permission] = ROLE_PERMISSIONS.get(self.current_user.role, frozenset())
        return perm in allowed


class HasAuthorization(Protocol):
    """Object that exposes authorization state."""

    @property
    def authz(self) -> AuthorizationService:
        """Return the authorization service."""
        ...


type CommandMethod[T: HasAuthorization, **P, R] = Callable[Concatenate[T, P], R]


class CommandDecorator(Protocol):
    """Decorator preserving any authorized command method signature."""

    def __call__[T: HasAuthorization, **P, R](
        self,
        fn: CommandMethod[T, P, R],
    ) -> CommandMethod[T, P, R]:
        """Decorate a command without changing its signature."""
        ...


class ParameterizedCommandDecorator[T: HasAuthorization, **P](Protocol):
    """Decorator bound to an authorized command's parameter signature."""

    def __call__[R](
        self,
        fn: CommandMethod[T, P, R],
    ) -> CommandMethod[T, P, R]:
        """Decorate a matching command while preserving its return type."""
        ...


@overload
def requires(
    permission: Permission,
    *,
    operation: AuthorizationOperation,
    target_resource_type: AuditResourceType,
    target_resource_id_resolver: None,
) -> CommandDecorator: ...


@overload
def requires[T: HasAuthorization, **P](
    permission: Permission,
    *,
    operation: AuthorizationOperation,
    target_resource_type: AuditResourceType,
    target_resource_id_resolver: Callable[Concatenate[T, P], object | None],
) -> ParameterizedCommandDecorator[T, P]: ...


def requires(
    permission: Permission,
    *,
    operation: AuthorizationOperation,
    target_resource_type: AuditResourceType,
    target_resource_id_resolver: Callable[..., object | None] | None,
) -> object:
    """Build a decorator that requires one permission and records authorization denials.

    Args:
        permission: Permission required before the wrapped command can run.
        operation: Stable name of the attempted workflow recorded on denial.
        target_resource_type: Audit resource family targeted by the workflow.
        target_resource_id_resolver: Optional callable receiving the decorated
            instance and method arguments. Its result is normalized to text and
            recorded as the target resource id. The resolver runs before the
            authorization decision so denied attempts retain their target.

    Returns:
        Signature-preserving command decorator. The wrapped method raises
        ``PermissionError`` when authorization fails. If its instance records
        application events, an ``AuthorizationDenied`` event is recorded first.
    """

    def deco[T: HasAuthorization, **P, R](
        fn: CommandMethod[T, P, R],
    ) -> CommandMethod[T, P, R]:
        """Decorate a command method with a single-permission check.

        Args:
            fn: Command method to wrap.

        Returns:
            Wrapped command method.
        """

        @wraps(fn)
        def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
            """Authorize and invoke the wrapped command method."""
            raw_resource_id = (
                target_resource_id_resolver(self, *args, **kwargs)
                if target_resource_id_resolver is not None
                else None
            )

            resource_id = str(raw_resource_id) if raw_resource_id is not None else None

            if self.authz.current_user is None:
                record_authorization_denied(
                    self,
                    (permission,),
                    operation=operation,
                    target_resource_type=target_resource_type,
                    target_resource_id=resource_id,
                )
                raise PermissionError("Unauthenticated")

            if not self.authz.has(permission):
                record_authorization_denied(
                    self,
                    (permission,),
                    operation=operation,
                    target_resource_type=target_resource_type,
                    target_resource_id=resource_id,
                )
                raise PermissionError(f"Missing permission: {permission.name}")
            return fn(self, *args, **kwargs)

        return wrapper

    return deco


@overload
def requires_all(
    *permissions: Permission,
    operation: AuthorizationOperation,
    target_resource_type: AuditResourceType,
    target_resource_id_resolver: None,
) -> CommandDecorator: ...


@overload
def requires_all[T: HasAuthorization, **P](
    *permissions: Permission,
    operation: AuthorizationOperation,
    target_resource_type: AuditResourceType,
    target_resource_id_resolver: Callable[Concatenate[T, P], object | None],
) -> ParameterizedCommandDecorator[T, P]: ...


def requires_all(
    *permissions: Permission,
    operation: AuthorizationOperation,
    target_resource_type: AuditResourceType,
    target_resource_id_resolver: Callable[..., object | None] | None,
) -> object:
    """Build a decorator that requires all permissions and records authorization denials.

    Args:
        permissions: Permissions required before the wrapped command can run.
        operation: Stable name of the attempted workflow recorded on denial.
        target_resource_type: Audit resource family targeted by the workflow.
        target_resource_id_resolver: Optional callable receiving the decorated
            instance and method arguments. Its result is normalized to text and
            recorded as the target resource id. The resolver runs before the
            authorization decision so denied attempts retain their target.

    Returns:
        Signature-preserving command decorator. The wrapped method raises
        ``PermissionError`` when any permission is missing. If its instance
        records application events, the event contains only the missing
        permissions, or every required permission when unauthenticated.
    """

    def deco[T: HasAuthorization, **P, R](
        fn: CommandMethod[T, P, R],
    ) -> CommandMethod[T, P, R]:
        """Decorate a command method with an all-permissions check.

        Args:
            fn: Command method to wrap.

        Returns:
            Wrapped command method.
        """

        @wraps(fn)
        def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
            """Authorize and invoke the wrapped command method."""
            raw_resource_id = (
                target_resource_id_resolver(self, *args, **kwargs)
                if target_resource_id_resolver is not None
                else None
            )

            resource_id = str(raw_resource_id) if raw_resource_id is not None else None

            if self.authz.current_user is None:
                record_authorization_denied(
                    self,
                    permissions,
                    operation=operation,
                    target_resource_type=target_resource_type,
                    target_resource_id=resource_id,
                )
                raise PermissionError("Unauthenticated")

            missing = [p for p in permissions if not self.authz.has(p)]

            if missing:
                record_authorization_denied(
                    self,
                    tuple(missing),
                    operation=operation,
                    target_resource_type=target_resource_type,
                    target_resource_id=resource_id,
                )
                names = ", ".join(p.name for p in missing)
                raise PermissionError(f"Missing permissions: {names}")

            return fn(self, *args, **kwargs)

        return wrapper

    return deco


def record_authorization_denied(
    target: object,
    required_permissions: tuple[Permission, ...],
    *,
    operation: AuthorizationOperation,
    target_resource_type: AuditResourceType,
    target_resource_id: object | None,
    occurred_at: datetime | None = None,
) -> None:
    """Record normalized denial metadata on an event-aware object.

    Objects that do not implement ``ApplicationEventRecorderMixin`` are
    intentionally ignored. This lets permission decorators protect ordinary
    command objects without requiring event infrastructure.

    Args:
        target: Candidate application-event recorder.
        required_permissions: Permissions responsible for the denial.
        operation: Stable name of the attempted workflow.
        target_resource_type: Audit resource family targeted by the attempt.
        target_resource_id: Optional target identifier; non-null values are
            normalized with ``str`` before recording.
        occurred_at: Explicit business timestamp. When omitted, the recorder's
            event clock supplies the timestamp.

    Returns:
        None.
    """
    if not isinstance(target, ApplicationEventRecorderMixin):
        return

    target.record_event(
        AuthorizationDenied(
            attempted_operation=operation,
            target_resource_type=target_resource_type,
            target_resource_id=(str(target_resource_id) if target_resource_id is not None else None),
            required_permissions=required_permissions,
            occurred_at=occurred_at or target.event_occurred_at(),
        )
    )
