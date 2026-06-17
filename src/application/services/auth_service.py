"""Authentication service for persisted users and runtime sessions."""

from src.adapters.driven.security.password_hasher import PasswordHash, hash_password, verify_password
from src.application.exceptions.application_errors import (
    NotFoundError,
    ValidationError,
)
from src.application.exceptions.password_errors import (
    CurrentPasswordIncorrectError,
    InvalidPersistedPasswordHashError,
    LoginInvalidPersistedPasswordHashError,
    LoginInvalidUserRuntimeError,
    LoginUserNotFoundError,
    LoginWrongPasswordError,
    PasswordChangeCriteriaNotMetError,
    PasswordChangeUserNotFoundError,
    PasswordResetCriteriaNotMetError,
    PasswordResetUserNotFoundError,
    PasswordUnchangedError,
    RegistrationInvalidUsernameError,
    RegistrationPasswordCriteriaNotMetError,
    RegistrationUsernameAlreadyExistsError,
)
from src.application.models.user_record import UserRecord
from src.application.services.runtime_user_factory import create_runtime_user_from_record
from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo
from src.ports.output.repository_errors import DuplicateKeyError
from src.ports.output.user_repository import UserRepositoryPort


class AuthService:
    """Handle registration, login, and password-management workflows."""

    def __init__(self, user_store: UserRepositoryPort) -> None:
        """Initialize the service with a user repository.

        Args:
            user_store: Repository used to persist and retrieve user records.
        """
        self._store = user_store
        self._current_user: User | None = None
        self.last_username: str | None = None

    @property
    def current_user(self) -> User | None:
        """Return the currently authenticated user, if any."""
        return self._current_user

    @property
    def user_repository(self) -> UserRepositoryPort:
        """Return the repository used for persisted user operations."""
        return self._store

    def register_user(
        self, username: str, role: Role, name: str, email: str, phone_number: str, password: str
    ) -> UserRecord:
        """Register a new user account.

        Authorization is enforced by the caller. This service assumes the caller
        has already applied any required RBAC checks.

        Args:
            username: Unique login name.
            role: Role assigned to the new user.
            name: Human-readable display name.
            email: Optional email address.
            phone_number: Optional phone number.
            password: Plain-text password to hash before storage.

        Returns:
            The persisted user record.

        Raises:
            RegistrationInvalidUsernameError: If the username or repository input is invalid.
            RegistrationUsernameAlreadyExistsError: If the username already exists.
            RegistrationPasswordCriteriaNotMetError: If the password fails validation.
        """
        clean_username = username.strip().lower()
        if not clean_username:
            raise RegistrationInvalidUsernameError()
        if self._store.get_by_username(clean_username) is not None:
            raise RegistrationUsernameAlreadyExistsError(username=clean_username)

        ci = ContactInfo(name=name, email=email or "", phone_number=phone_number or "")
        clean_name = ci.name
        clean_email = ci.email
        clean_phone = ci.phone_number
        try:
            ph = hash_password(password)
        except ValueError as exc:
            raise RegistrationPasswordCriteriaNotMetError(str(exc), username=clean_username) from exc
        role_value = role.value
        try:
            return self._store.create(
                username=clean_username,
                role=role_value,
                name=clean_name,
                email=clean_email,
                phone_number=clean_phone,
                password_hash=ph,
            )
        except DuplicateKeyError as exc:
            raise RegistrationUsernameAlreadyExistsError(username=clean_username) from exc
        except ValueError as exc:
            raise RegistrationInvalidUsernameError(str(exc), username=clean_username) from exc

    def _set_password(self, username: str, new_password: str) -> None:
        """Set a new password through the repository's atomic revocation boundary."""
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        try:
            password_hash = hash_password(new_password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        try:
            self._store.update_password(username, password_hash)
        except ValueError as exc:
            raise NotFoundError("User not found.") from exc

    def login(self, username: str, password: str) -> tuple[UserRecord, User]:
        """Authenticate a user and hydrate the runtime user entity.

        Args:
            username: Login username.
            password: Plain-text password supplied by the user.

        Returns:
            The authenticated runtime user entity along with its record.

        Raises:
            LoginUserNotFoundError: If the username is unknown.
            LoginInvalidPersistedPasswordHashError: If the stored password hash is invalid.
            LoginWrongPasswordError: If the password is invalid.
            LoginInvalidUserRuntimeError: If persisted user data cannot hydrate a runtime user.
        """
        rec, user = self.authenticate(username, password)

        self._current_user = user
        self.last_username = rec.username
        return rec, user

    def authenticate(self, username: str, password: str) -> tuple[UserRecord, User]:
        """Verify credentials and return the persisted record plus runtime user without mutating session.

        Args:
            username: Login username.
            password: Plain-text password supplied by the user.

        Returns:
            A tuple containing the persisted user record and the hydrated runtime user entity.

        Raises:
            LoginUserNotFoundError: If the username is unknown.
            LoginInvalidPersistedPasswordHashError: If the stored password hash is invalid.
            LoginWrongPasswordError: If the password is invalid.
            LoginInvalidUserRuntimeError: If persisted user data cannot hydrate a runtime user.
        """
        rec = self._store.get_by_username(username)

        if not rec:
            raise LoginUserNotFoundError(user_id=None, username=username)

        try:
            ok = verify_password(password, PasswordHash.parse(rec.password))
        except (TypeError, ValueError) as exc:
            raise LoginInvalidPersistedPasswordHashError(user_id=rec.user_id, username=rec.username) from exc
        if not ok:
            raise LoginWrongPasswordError(user_id=rec.user_id, username=rec.username)

        try:
            user = create_runtime_user_from_record(rec)
        except ValueError as exc:
            raise LoginInvalidUserRuntimeError(str(exc), user_id=rec.user_id, username=rec.username) from exc
        return rec, user

    def logout(self) -> None:
        """Clear the active authentication session."""
        self._current_user = None
        self.last_username = None

    def change_password(self, username: str, old_password: str, new_password: str) -> UserRecord:
        """Change a password after verifying the old password.

        Args:
            username: Username whose password should change.
            old_password: Existing password used for verification.
            new_password: Replacement plain-text password.

        Returns:
            The target user record.

        Raises:
            PasswordChangeUserNotFoundError: If the user does not exist.
            InvalidPersistedPasswordHashError: If the stored password hash is invalid.
            CurrentPasswordIncorrectError: If the old password is wrong.
            PasswordUnchangedError: If the new password matches the old password.
            PasswordChangeCriteriaNotMetError: If the new password fails validation.
        """

        rec = self._store.get_by_username(username)
        if not rec:
            raise PasswordChangeUserNotFoundError(user_id=None, username=username)

        try:
            password_hash = PasswordHash.parse(rec.password)
        except (TypeError, ValueError) as exc:
            raise InvalidPersistedPasswordHashError(user_id=rec.user_id, username=rec.username) from exc

        if not verify_password(old_password, password_hash):
            raise CurrentPasswordIncorrectError(user_id=rec.user_id, username=rec.username)

        if verify_password(new_password, password_hash):
            raise PasswordUnchangedError(user_id=rec.user_id, username=rec.username)

        try:
            self._set_password(username, new_password)
        except ValidationError as exc:
            raise PasswordChangeCriteriaNotMetError(
                message=str(exc),
                user_id=rec.user_id,
                username=rec.username,
            ) from exc
        except NotFoundError:
            raise PasswordChangeUserNotFoundError(user_id=rec.user_id, username=rec.username) from None

        return rec

    def reset_password(self, username: str, new_password: str) -> UserRecord:
        """Reset a password without verifying the old password.

        Args:
            username: Username whose password should change.
            new_password: Replacement plain-text password.

        Returns:
            The target user record.

        Raises:
            PasswordResetUserNotFoundError: If the user does not exist.
            PasswordResetCriteriaNotMetError: If the new password fails validation.
        """

        rec = self._store.get_by_username(username)
        if not rec:
            raise PasswordResetUserNotFoundError(user_id=None, username=username)

        try:
            self._set_password(username, new_password)
        except ValidationError as exc:
            raise PasswordResetCriteriaNotMetError(
                message=str(exc),
                user_id=rec.user_id,
                username=rec.username,
            ) from exc
        except NotFoundError:
            raise PasswordResetUserNotFoundError(user_id=rec.user_id, username=rec.username) from None

        return rec
