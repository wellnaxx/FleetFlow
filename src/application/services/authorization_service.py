"""Permission checks and decorators for command authorization."""

from collections.abc import Callable
from functools import wraps
from typing import Concatenate, Protocol

from src.domain.entities.users.user import User
from src.domain.enums.auth import ROLE_PERMISSIONS, Permission


class AuthorizationService:
    """Tracks current user and exposes permission checks."""

    def __init__(self, current_user: User | None) -> None:
        """Initialize authorization state.

        Args:
            current_user: Current runtime user, or `None` when unauthenticated.
        """
        self.current_user: User | None = current_user

    def has(self, perm: Permission) -> bool:
        """Return whether the current user has a permission.

        Args:
            perm: Permission to check.

        Returns:
            True when a current user exists and their role grants the permission.
        """
        if not self.current_user:
            return False
        allowed: set[Permission] = ROLE_PERMISSIONS.get(self.current_user.role, set())
        return perm in allowed


class HasAuthorization(Protocol):
    """Object that exposes authorization state."""

    @property
    def authz(self) -> AuthorizationService:
        """Return the authorization service."""
        ...


type CommandMethod[T: HasAuthorization, **P, R] = Callable[Concatenate[T, P], R]
type CommandDecorator[T: HasAuthorization, **P, R] = Callable[
    [CommandMethod[T, P, R]],
    CommandMethod[T, P, R],
]


def requires[T: HasAuthorization, **P, R](permission: Permission) -> CommandDecorator[T, P, R]:
    """Build a decorator that requires one permission.

    Args:
        permission: Permission required before the wrapped command can run.

    Returns:
        Decorator that raises PermissionError when authorization fails.
    """

    def deco(fn: CommandMethod[T, P, R]) -> CommandMethod[T, P, R]:
        """Decorate a command method with a single-permission check.

        Args:
            fn: Command method to wrap.

        Returns:
            Wrapped command method.
        """

        @wraps(fn)
        def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
            """Authorize and invoke the wrapped command method."""
            if self.authz.current_user is None:
                raise PermissionError("Unauthenticated")

            if not self.authz.has(permission):
                raise PermissionError(f"Missing permission: {permission.name}")
            return fn(self, *args, **kwargs)

        return wrapper

    return deco


def requires_all[T: HasAuthorization, **P, R](*permissions: Permission) -> CommandDecorator[T, P, R]:
    """Build a decorator that requires all permissions.

    Args:
        permissions: Permissions required before the wrapped command can run.

    Returns:
        Decorator that raises PermissionError when authorization fails.
    """

    def deco(fn: CommandMethod[T, P, R]) -> CommandMethod[T, P, R]:
        """Decorate a command method with an all-permissions check.

        Args:
            fn: Command method to wrap.

        Returns:
            Wrapped command method.
        """

        @wraps(fn)
        def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
            """Authorize and invoke the wrapped command method."""
            if self.authz.current_user is None:
                raise PermissionError("Unauthenticated")

            missing = [p for p in permissions if not self.authz.has(p)]

            if missing:
                names = ", ".join(p.name for p in missing)
                raise PermissionError(f"Missing permissions: {names}")

            return fn(self, *args, **kwargs)

        return wrapper

    return deco
