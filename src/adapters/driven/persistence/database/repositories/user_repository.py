from src.adapters.driven.persistence.database.executor import (
    execute_insert,
    execute_returning_one,
    execute_write,
    fetch_all,
    fetch_one,
)
from src.adapters.driven.persistence.database.mappers import map_user_record
from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class PostgresUserRepository:
    """Postgres-backed user repository implementation."""

    @staticmethod
    def _normalize_username(username: str | None) -> str:
        """Normalize a username for case-insensitive lookup.

        Args:
            username: Raw username, or `None`.

        Returns:
            Lowercase trimmed username, or an empty string.
        """
        return (username or "").strip().lower()

    @staticmethod
    def _normalize_role(role: object) -> str:
        """Normalize a role enum or role string into the persisted role value.

        Args:
            role: Runtime role enum or persisted role string.

        Returns:
            Persisted role value.

        Raises:
            TypeError: If role is not a role enum or string.
            ValueError: If role is not a supported application role.
        """
        if isinstance(role, Role):
            return role.value
        if not isinstance(role, str):
            raise TypeError(f"Invalid role: {role!r}")
        try:
            return Role(role.strip().upper()).value
        except ValueError as exc:
            raise ValueError(f"Invalid role: {role!r}") from exc

    def get_by_username(self, username: str) -> UserRecord | None:
        """Return a user by username.

        Args:
            username: Username to look up case-insensitively.

        Returns:
            Matching user record, or `None` when absent.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required user column is missing.
            TypeError: If a required user column has an unexpected type.
        """
        normalized_username = self._normalize_username(username)
        if not normalized_username:
            return None

        user_row = fetch_one(QUERIES.users.get_by_username, (normalized_username,))

        return map_user_record(user_row) if user_row is not None else None

    def create(
        self, username: str, role: str, name: str, email: str, phone_number: str, password_hash: PasswordHash
    ) -> UserRecord:
        """Create and persist a user record.

        Args:
            username: Unique login name.
            role: Role enum or persisted role string.
            name: User display name.
            email: Optional email address.
            phone_number: Optional phone number.
            password_hash: Password hash to persist.

        Returns:
            Created user record with its database-allocated id.

        Raises:
            DatabaseError: If the insert fails or does not return an id.
            TypeError: If role or password hash has the wrong type.
            ValueError: If validation fails or username already exists.
        """
        raw_username = (username or "").strip()
        normalized_username = self._normalize_username(username)

        if not normalized_username:
            raise ValueError("Username is required.")
        if self.get_by_username(normalized_username) is not None:
            raise ValueError("Username already exists.")

        role_value = self._normalize_role(role)
        contact = ContactInfo(name=name, email=email, phone_number=phone_number)

        try:
            pw_serialized = password_hash.serialize()
        except AttributeError as e:
            raise TypeError("password_hash must be a PasswordHash") from e

        user_id = execute_insert(
            QUERIES.users.add,
            (
                raw_username,
                role_value,
                contact.name,
                contact.email,
                contact.phone_number,
                pw_serialized,
            ),
        )

        return UserRecord(
            user_id=user_id,
            username=raw_username,
            role=role_value,
            name=contact.name,
            email=contact.email,
            phone_number=contact.phone_number,
            password=pw_serialized,
            token_version=1,
        )

    def update_password(self, username: str, new_hash: PasswordHash) -> None:
        """Replace a user's persisted password hash.

        Args:
            username: Username whose password should change.
            new_hash: Replacement password hash.

        Returns:
            None.

        Raises:
            DatabaseError: If the update operation fails.
            ValueError: If the user does not exist.
        """
        normalized_username = self._normalize_username(username)
        user_record_row = self.get_by_username(normalized_username)
        if user_record_row is None:
            raise ValueError(f"User with username {username} not found")
        execute_write(QUERIES.users.update_password, (new_hash.serialize(), normalized_username))

    def save(self) -> None:
        """Persist pending changes.

        The Postgres implementation writes immediately, so this is a no-op.

        Returns:
            None.
        """
        return

    def list_users(self) -> list[UserRecord]:
        """Return all registered users.

        Returns:
            All persisted user records ordered by user id.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required user column is missing.
            TypeError: If a required user column has an unexpected type.
        """
        user_rows = fetch_all(QUERIES.users.list_all)
        return [map_user_record(user_row) for user_row in user_rows]

    def get_by_id(self, user_id: int) -> UserRecord | None:
        """Return a user by their database id, or `None` when absent.

        Args:
            user_id: Database ID to look up.

        Returns:
            Matching user record, or `None`.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required user column is missing.
            TypeError: If a required user column has an unexpected type.
        """
        user_row = fetch_one(QUERIES.users.get_by_id, (user_id,))
        return map_user_record(user_row) if user_row is not None else None

    def increment_token_version_by_id(self, user_id: int) -> UserRecord | None:
        """Increment a user's token version by their database id to invalidate existing tokens.

        Args:
            user_id: Database ID of the user whose token version should increment.

        Returns:
            Updated user record, or `None` if no matching user was found.

        Raises:
            DatabaseError: If the update or select operation fails.
            KeyError: If a required user column is missing.
            TypeError: If a required user column has an unexpected type.
        """
        row = execute_returning_one(QUERIES.users.increment_token_version_by_id, (user_id,))
        return map_user_record(row) if row is not None else None

    def increment_token_version_by_username(self, username: str) -> UserRecord | None:
        """Increment a user's token version by their username to invalidate existing tokens.

        Args:
            username: Username whose token version should increment.

        Returns:
            Updated user record, or `None` if no matching user was found.

        Raises:
            DatabaseError: If the update or select operation fails.
            KeyError: If a required user column is missing.
            TypeError: If a required user column has an unexpected type.
        """
        normalized_username = self._normalize_username(username)

        row = execute_returning_one(QUERIES.users.increment_token_version_by_username, (normalized_username,))
        return map_user_record(row) if row is not None else None
