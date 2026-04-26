"""Output port for persisted user repository adapters."""

from typing import Protocol

from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord


class UserRepositoryPort(Protocol):
    """Persist and query registered application users."""

    def get(self, username: str) -> UserRecord | None:
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
        """Replace a user's stored password hash.

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
