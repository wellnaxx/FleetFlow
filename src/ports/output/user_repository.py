"""Output port for persisted user repository adapters."""

from typing import Protocol

from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord


class UserRepositoryPort(Protocol):
    """Persist and query registered application users."""

    def get_by_username(self, username: str) -> UserRecord | None:
        """Return a user by username, or `None` when absent.

        Args:
            username: Username to look up.

        Returns:
            Matching user record, or `None`.
        """
        ...

    def create(
        self,
        username: str,
        role: str,
        name: str,
        email: str,
        phone_number: str,
        password_hash: PasswordHash,
    ) -> UserRecord:
        """Create, persist, and return a user record.

        Args:
            username: Unique login name.
            role: Persisted role value.
            name: User display name.
            email: Optional email address.
            phone_number: Optional phone number.
            password_hash: Password hash to persist.

        Returns:
            Created user record.
        """
        ...

    def update_password(self, username: str, new_hash: PasswordHash) -> None:
        """Atomically replace a user's stored password hash and revoke existing tokens.

        Implementations must increment the user's token version in the same
        persistence operation that stores the new password hash. Callers must
        not additionally call `increment_token_version_by_id` or
        `increment_token_version_by_username` after this method; doing so would
        advance the version twice and invalidate newly issued tokens.

        Args:
            username: Username whose password should change.
            new_hash: Replacement password hash.
        """
        ...

    def save(self) -> str | None:
        """Flush repository state to durable storage when supported."""
        ...

    def list_users(self) -> list[UserRecord]:
        """Return all registered users."""
        ...

    def get_by_id(self, user_id: int) -> UserRecord | None:
        """Return a user by their database id, or `None` when absent.

        Args:
            user_id: Database ID to look up.

        Returns:
            Matching user record, or `None`.
        """
        ...

    def increment_token_version_by_id(self, user_id: int) -> UserRecord | None:
        """Increment a user's token version by their id to invalidate existing tokens.

        Args:
            user_id: Database ID of the user whose token version should increment.

        Returns:
            Updated user record, or `None` if no matching user was found.
        """
        ...

    def increment_token_version_by_username(self, username: str) -> UserRecord | None:
        """Increment a user's token version by their username to invalidate existing tokens.

        Args:
            username: Username whose token version should increment.

        Returns:
            Updated user record, or `None` if no matching user was found.
        """
        ...
