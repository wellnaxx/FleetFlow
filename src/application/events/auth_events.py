"""Application events describing authentication and user-management workflows."""

from dataclasses import dataclass

from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.enums.user_login_rejection_reasons import UserLoginRejectionReason
from src.application.enums.user_password_change_rejection_reasons import UserPasswordChangeRejectionReason
from src.application.enums.user_password_reset_rejection_reasons import UserPasswordResetRejectionReason
from src.application.enums.user_registration_rejection_reasons import UserRegistrationRejectionReason
from src.application.events.base import ApplicationEvent
from src.domain.enums.auth import Permission, Role


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRegistered(ApplicationEvent):
    """Event recorded when a new user account is registered."""

    user_id: int
    username: str
    role: Role


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRegistrationRejected(ApplicationEvent):
    """Event recorded when a user registration attempt is rejected."""

    username: str | None
    reason: UserRegistrationRejectionReason


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPasswordChanged(ApplicationEvent):
    """Event recorded when a user changes their password."""

    user_id: int
    username: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPasswordChangeRejected(ApplicationEvent):
    """Event recorded when a user password change attempt is rejected."""

    user_id: int | None
    username: str | None
    reason: UserPasswordChangeRejectionReason


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPasswordReset(ApplicationEvent):
    """Event recorded when an administrator resets a user's password."""

    user_id: int
    username: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPasswordResetRejected(ApplicationEvent):
    """Event recorded when an administrator's attempt to reset a user's password is rejected."""

    user_id: int | None
    username: str | None
    reason: UserPasswordResetRejectionReason


@dataclass(frozen=True, slots=True, kw_only=True)
class UserAuthenticated(ApplicationEvent):
    """Event recorded when password authentication succeeds."""

    user_id: int
    username: str
    role: Role


@dataclass(frozen=True, slots=True, kw_only=True)
class UserLoginRejected(ApplicationEvent):
    """Event recorded when password authentication is rejected."""

    user_id: int | None
    username: str | None
    reason: UserLoginRejectionReason


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
