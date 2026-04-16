from collections.abc import Callable
from functools import wraps
from typing import Any

from domain.entities.users.user import User
from domain.enums.auth import ROLE_PERMISSIONS, Permission, Role


class AuthorizationService:
    """Tracks current user and exposes permission checks."""

    def __init__(self, current_user: User | None) -> None:
        self.current_user: User | None = current_user

    def has(self, perm: Permission) -> bool:
        if not self.current_user:
            return False
        role: Role | None = getattr(self.current_user, "role", None)
        if role is None:
            return False
        allowed: set[Permission] = ROLE_PERMISSIONS.get(role, set())
        return perm in allowed


def requires(permission: Permission) -> Callable[..., Any]:
    """Decorator: ensure the current user has the given permission."""

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            authz: AuthorizationService | None = getattr(self, "authz", None)
            if not authz or not authz.has(permission):
                raise PermissionError(f"Missing permission: {permission.name}")
            return fn(self, *args, **kwargs)

        return wrapper

    return deco


def requires_all(*permissions: Permission) -> Callable[..., Any]:
    """Decorator: ensure the current user has all of the given permissions."""

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            authz: AuthorizationService | None = getattr(self, "authz", None)
            if not authz:
                raise PermissionError("Not authenticated")
            missing = [p for p in permissions if not authz.has(p)]
            if missing:
                raise PermissionError(f"Missing permission: {missing[0].name}")
            return fn(self, *args, **kwargs)

        return wrapper

    return deco
