from src.adapters.driven.security.password_hasher import PasswordHash, hash_password, verify_password
from src.application.models.user_record import UserRecord
from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager
from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo
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
            ValueError: If validation fails or the repository rejects the user.
        """
        ci = ContactInfo(name=name, email=email or "", phone_number=phone_number)
        clean_name = ci.name
        clean_email = ci.email
        clean_phone = ci.phone_number
        ph = hash_password(password)
        role_value = role.value
        return self._store.create(
            username=username,
            role=role_value,
            name=clean_name,
            email=clean_email,
            phone_number=clean_phone,
            password_hash=ph,
        )

    def _set_password(self, username: str, new_password: str) -> None:
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        self._store.update_password(username, hash_password(new_password))

    def login(self, username: str, password: str) -> User:
        """Authenticate a user and hydrate the runtime user entity.

        Args:
            username: Login username.
            password: Plain-text password supplied by the user.

        Returns:
            The authenticated runtime user entity.

        Raises:
            ValueError: If the username is unknown or the password is invalid.
        """
        rec = self._store.get(username)
        if not rec:
            raise ValueError("Invalid username or password.")
        ok = verify_password(password, PasswordHash.parse(rec.password))
        if not ok:
            raise ValueError("Invalid username or password.")

        contact = ContactInfo(name=rec.name, email=rec.email, phone_number=rec.phone_number)

        try:
            role = Role(rec.role)
        except ValueError as exc:
            raise ValueError(f"Invalid persisted role for user {rec.username!r}: {rec.role!r}") from exc

        if role == Role.MANAGER:
            self._current_user = Manager(
                rec.user_id,
                contact.name,
                contact.email,
                contact.phone_number,
            )
        elif role == Role.EMPLOYEE:
            self._current_user = Employee(
                rec.user_id,
                contact.name,
                contact.email,
                contact.phone_number,
            )
        else:
            raise ValueError(f"Unsupported role: {role}")

        self.last_username = rec.username
        return self._current_user

    def logout(self) -> None:
        """Clear the active authentication session."""
        self._current_user = None
        self.last_username = None

    def change_password(self, username: str, old_password: str, new_password: str) -> None:
        """Change a password after verifying the old password.

        Args:
            username: Username whose password should change.
            old_password: Existing password used for verification.
            new_password: Replacement plain-text password.

        Raises:
            ValueError: If the user is missing, the old password is wrong, or
                the new password is invalid.
        """
        rec = self._store.get(username)
        if not rec:
            raise ValueError("User not found.")
        if not verify_password(old_password, PasswordHash.parse(rec.password)):
            raise ValueError("Old password incorrect.")
        if verify_password(new_password, PasswordHash.parse(rec.password)):
            raise ValueError("New password must be different from the old one.")
        self._set_password(username, new_password)

    def reset_password(self, username: str, new_password: str) -> None:
        """Reset a password without verifying the old password.

        Args:
            username: Username whose password should change.
            new_password: Replacement plain-text password.

        Raises:
            ValueError: If the user is missing or the password is invalid.
        """
        rec = self._store.get(username)
        if not rec:
            raise ValueError("User not found.")
        self._set_password(username, new_password)
