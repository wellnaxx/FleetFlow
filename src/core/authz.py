from functools import wraps
from src.models.auth import ROLE_PERMISSIONS, Permission

class AuthorizationService:
    """Tracks current user and exposes permission checks."""
    def __init__(self, current_user):
        self.current_user = current_user

    def has(self, perm: Permission) -> bool:
        if not self.current_user:
            return False
        allowed = ROLE_PERMISSIONS.get(getattr(self.current_user, "role", None), set())
        return perm in allowed

def requires(permission: Permission):
    """Decorator: ensure the current user has the given permission."""
    def deco(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            authz = getattr(self, "authz", None)
            if not authz or not authz.has(permission):
                raise PermissionError(f"Missing permission: {permission.name}")
            return fn(self, *args, **kwargs)
        return wrapper
    return deco

def requires_all(*permissions):
    """Decorator: ensure the current user has all of the given permissions."""
    def deco(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            authz = getattr(self, "authz", None)
            if not authz:
                raise PermissionError("Not authenticated")
            missing = [p for p in permissions if not authz.has(p)]
            if missing:
                # report the first missing or list them all; your choice
                raise PermissionError(f"Missing permission: {missing[0].name}")
            return fn(self, *args, **kwargs)
        return wrapper
    return deco