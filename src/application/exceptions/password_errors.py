"""Typed authentication and password-management errors carrying audit rejection reasons."""

from src.application.enums.user_login_rejection_reasons import UserLoginRejectionReason
from src.application.enums.user_password_change_rejection_reasons import UserPasswordChangeRejectionReason
from src.application.enums.user_password_reset_rejection_reasons import UserPasswordResetRejectionReason
from src.application.enums.user_registration_rejection_reasons import UserRegistrationRejectionReason
from src.application.exceptions.application_errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class PasswordChangeRejectedMixin:
    """Common metadata exposed by password-change rejection errors."""

    reason: UserPasswordChangeRejectionReason
    user_id: int | None
    username: str | None


class PasswordResetRejectedMixin:
    """Common metadata exposed by password-reset rejection errors."""

    reason: UserPasswordResetRejectionReason
    user_id: int | None
    username: str | None


class LoginRejectedMixin:
    """Common metadata exposed by login rejection errors."""

    reason: UserLoginRejectionReason
    user_id: int | None
    username: str | None


class RegistrationRejectedMixin:
    """Common metadata exposed by registration rejection errors."""

    reason: UserRegistrationRejectionReason
    username: str | None


class PasswordChangeInvalidUsernameError(ValidationError, PasswordChangeRejectedMixin):
    """Raised when a password change targets an invalid username."""

    def __init__(self, *, username: str | None) -> None:
        super().__init__("Username must be a non-empty string.")
        self.reason = UserPasswordChangeRejectionReason.INVALID_USERNAME
        self.user_id = None
        self.username = username


class PasswordChangeUserNotFoundError(NotFoundError, PasswordChangeRejectedMixin):
    """Raised when a password change targets a missing user."""

    def __init__(self, user_id: int | None, username: str) -> None:
        super().__init__("User not found.")
        self.reason = UserPasswordChangeRejectionReason.USER_NOT_FOUND
        self.user_id = user_id
        self.username = username


class InvalidPersistedPasswordHashError(ValidationError, PasswordChangeRejectedMixin):
    """Raised when a stored password hash cannot be parsed."""

    def __init__(self, user_id: int, username: str) -> None:
        super().__init__("Invalid persisted password hash.")
        self.reason = UserPasswordChangeRejectionReason.INVALID_PASSWORD_HASH
        self.user_id = user_id
        self.username = username


class CurrentPasswordIncorrectError(AuthenticationError, PasswordChangeRejectedMixin):
    """Raised when the supplied current password does not match."""

    def __init__(self, user_id: int, username: str) -> None:
        super().__init__("Old password incorrect.")
        self.reason = UserPasswordChangeRejectionReason.CURRENT_PASSWORD_INCORRECT
        self.user_id = user_id
        self.username = username


class PasswordChangeCriteriaNotMetError(ValidationError, PasswordChangeRejectedMixin):
    """Raised when a replacement password fails the password policy."""

    def __init__(self, message: str, *, user_id: int, username: str) -> None:
        super().__init__(message)
        self.reason = UserPasswordChangeRejectionReason.PASSWORD_CRITERIA_NOT_MET
        self.user_id = user_id
        self.username = username


class PasswordUnchangedError(ValidationError, PasswordChangeRejectedMixin):
    """Raised when a replacement password matches the current password."""

    def __init__(self, user_id: int, username: str) -> None:
        super().__init__("New password must be different from the old one.")
        self.reason = UserPasswordChangeRejectionReason.SAME_AS_CURRENT_PASSWORD
        self.user_id = user_id
        self.username = username


class PasswordResetInvalidUsernameError(ValidationError, PasswordResetRejectedMixin):
    """Raised when a password reset targets an invalid username."""

    def __init__(self, *, username: str | None) -> None:
        super().__init__("Username must be a non-empty string.")
        self.reason = UserPasswordResetRejectionReason.INVALID_USERNAME
        self.user_id = None
        self.username = username


class PasswordResetUserNotFoundError(NotFoundError, PasswordResetRejectedMixin):
    """Raised when a password reset targets a missing user."""

    def __init__(self, user_id: int | None, username: str) -> None:
        super().__init__("User not found.")
        self.reason = UserPasswordResetRejectionReason.USER_NOT_FOUND
        self.user_id = user_id
        self.username = username


class PasswordResetCriteriaNotMetError(ValidationError, PasswordResetRejectedMixin):
    """Raised when a reset password fails the password policy."""

    def __init__(self, message: str, *, user_id: int, username: str) -> None:
        super().__init__(message)
        self.reason = UserPasswordResetRejectionReason.PASSWORD_CRITERIA_NOT_MET
        self.user_id = user_id
        self.username = username


class CannotResetOwnPasswordError(ConflictError, PasswordResetRejectedMixin):
    """Raised when a user attempts to reset their own password through the admin reset flow."""

    def __init__(self, user_id: int, username: str) -> None:
        super().__init__("You cannot reset your own password.")
        self.reason = UserPasswordResetRejectionReason.CANNOT_RESET_OWN_PASSWORD
        self.user_id = user_id
        self.username = username


class LoginUserNotFoundError(AuthenticationError, LoginRejectedMixin):
    """Raised when login targets a username that does not exist."""

    def __init__(self, user_id: int | None, username: str) -> None:
        super().__init__("Invalid username or password.")
        self.reason = UserLoginRejectionReason.USER_NOT_FOUND
        self.user_id = user_id
        self.username = username


class LoginInvalidPersistedPasswordHashError(ValidationError, LoginRejectedMixin):
    """Raised when login finds a stored password hash that cannot be parsed."""

    def __init__(self, user_id: int, username: str) -> None:
        super().__init__("Invalid persisted password hash.")
        self.reason = UserLoginRejectionReason.INVALID_PASSWORD_HASH
        self.user_id = user_id
        self.username = username


class LoginWrongPasswordError(AuthenticationError, LoginRejectedMixin):
    """Raised when login receives a password that does not match."""

    def __init__(self, user_id: int, username: str) -> None:
        super().__init__("Invalid username or password.")
        self.reason = UserLoginRejectionReason.INVALID_PASSWORD
        self.user_id = user_id
        self.username = username


class LoginInvalidUserRuntimeError(ValidationError, LoginRejectedMixin):
    """Raised when login cannot hydrate persisted user data into a current-user principal."""

    def __init__(self, message: str, *, user_id: int, username: str) -> None:
        super().__init__(message)
        self.reason = UserLoginRejectionReason.INVALID_RUNTIME_USER
        self.user_id = user_id
        self.username = username


class RegistrationInvalidUsernameError(ValidationError, RegistrationRejectedMixin):
    """Raised when registration receives an invalid username."""

    def __init__(self, message: str = "Username is required.", *, username: str | None = None) -> None:
        super().__init__(message)
        self.reason = UserRegistrationRejectionReason.INVALID_USERNAME
        self.username = username


class RegistrationUsernameAlreadyExistsError(ConflictError, RegistrationRejectedMixin):
    """Raised when registration targets an existing username."""

    def __init__(self, username: str) -> None:
        super().__init__("Username already exists.")
        self.reason = UserRegistrationRejectionReason.USERNAME_ALREADY_EXISTS
        self.username = username


class RegistrationPasswordCriteriaNotMetError(ValidationError, RegistrationRejectedMixin):
    """Raised when a registration password fails the password policy."""

    def __init__(self, message: str, *, username: str) -> None:
        super().__init__(message)
        self.reason = UserRegistrationRejectionReason.PASSWORD_CRITERIA_NOT_MET
        self.username = username
