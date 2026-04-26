"""Permission checks and decorators for command authorization."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from src.domain.entities.users.user import User
from src.domain.enums.auth import ROLE_PERMISSIONS, Permission, Role


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
        role: Role | None = getattr(self.current_user, "role", None)
        if role is None:
            return False
        allowed: set[Permission] = ROLE_PERMISSIONS.get(role, set())
        return perm in allowed


def requires(permission: Permission) -> Callable[..., Any]:
    """Build a decorator that requires one permission.

    Args:
        permission: Permission required before the wrapped command can run.

    Returns:
        Decorator that raises PermissionError when authorization fails.
    """

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorate a command method with a single-permission check.

        Args:
            fn: Command method to wrap.

        Returns:
            Wrapped command method.
        """

        @wraps(fn)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            """Authorize and invoke the wrapped command method."""
            authz: AuthorizationService | None = getattr(self, "authz", None)
            if not authz or not authz.has(permission):
                raise PermissionError(f"Missing permission: {permission.name}")
            return fn(self, *args, **kwargs)

        return wrapper

    return deco


def requires_all(*permissions: Permission) -> Callable[..., Any]:
    """Build a decorator that requires all permissions.

    Args:
        permissions: Permissions required before the wrapped command can run.

    Returns:
        Decorator that raises PermissionError when authorization fails.
    """

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorate a command method with an all-permissions check.

        Args:
            fn: Command method to wrap.

        Returns:
            Wrapped command method.
        """

        @wraps(fn)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            """Authorize and invoke the wrapped command method."""
            authz: AuthorizationService | None = getattr(self, "authz", None)
            if not authz:
                raise PermissionError("Not authenticated")
            missing = [p for p in permissions if not authz.has(p)]
            if missing:
                raise PermissionError(f"Missing permission: {missing[0].name}")
            return fn(self, *args, **kwargs)

        return wrapper

    return deco
