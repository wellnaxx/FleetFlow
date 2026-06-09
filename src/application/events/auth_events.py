"""Application events describing authentication and user-management workflows."""

from dataclasses import dataclass

from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.events.base import ApplicationEvent
from src.domain.enums.auth import Permission, Role


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRegistered(ApplicationEvent):
    """Event recorded when a new user account is registered."""

    user_id: int
    username: str
    role: Role


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPasswordChanged(ApplicationEvent):
    """Event recorded when a user changes their password."""

    user_id: int
    username: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPasswordReset(ApplicationEvent):
    """Event recorded when an administrator resets a user's password."""

    user_id: int
    username: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserAuthenticated(ApplicationEvent):
    """Event recorded when password authentication succeeds."""

    user_id: int
    username: str
    role: Role


@dataclass(frozen=True, slots=True, kw_only=True)
class UserLoginRejected(ApplicationEvent):
    """Event recorded when password authentication is rejected."""

    username: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserSessionEnded(ApplicationEvent):
    """Event recorded when a local application session ends."""

    user_id: int
    username: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserTokensRevoked(ApplicationEvent):
    """Event recorded when all outstanding tokens for a user are invalidated."""

    user_id: int
    username: str
    reason: TokenRevocationReason


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorizationDenied(ApplicationEvent):
    """Event recorded when an authorization decision denies an operation."""

    user_id: int | None
    username: str | None
    required_permissions: tuple[Permission, ...]
