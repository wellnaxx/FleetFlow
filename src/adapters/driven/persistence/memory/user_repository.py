"""In-memory implementation of user persistence for tests and local runtime."""

from dataclasses import replace

from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo
from src.ports.output.repository_errors import DuplicateKeyError


class InMemoryUserRepository:
    """In-memory user repository keyed by normalized username.

    User ids use a create-time allocation model: `create()` assigns and commits
    the next id directly. Unlike the customer/package/route repos, this
    repository does not expose a peek-then-add id workflow.
    """

    def __init__(self) -> None:
        """Initialize an empty repository with ids starting at one."""
        self._by_username: dict[str, UserRecord] = {}
        self._by_id: dict[int, UserRecord] = {}
        self._next_id = 1

    @staticmethod
    def _normalize_username(username: str | None) -> str:
        return (username or "").strip().lower()

    def get_by_username(self, username: str) -> UserRecord | None:
        """Fetch a persisted user by username.

        Args:
            username: Username to look up case-insensitively.

        Returns:
            The matching user record, or `None` when absent.
        """
        key = self._normalize_username(username)
        if not key:
            return None
        return self._by_username.get(key)

    def create(
        self,
        username: str,
        role: Role | str,
        name: str,
        email: str,
        phone_number: str,
        password_hash: PasswordHash,
    ) -> UserRecord:
        """Create and persist a user record.

        Args:
            username: Unique login name.
            role: Role enum or persisted role string.
            name: User display name.
            email: Optional email address.
            phone_number: Optional phone number.
            password_hash: Serialized-hash value object.

        Returns:
            The newly created user record.

        Raises:
            TypeError: If the role or password hash has the wrong type.
            ValueError: If validation fails.
            DuplicateKeyError: If the username already exists.
        """
        raw_username = (username or "").strip()
        norm = self._normalize_username(username)

        if not norm:
            raise ValueError("Username is required.")
        if norm in self._by_username:
            raise DuplicateKeyError("Username already exists.")

        role_value = InMemoryUserRepository._normalize_role(role)
        ci = ContactInfo(name=name, email=email, phone_number=phone_number)

        try:
            pw_serialized = password_hash.serialize()
        except AttributeError as e:
            raise TypeError("password_hash must be a PasswordHash") from e

        rec = UserRecord(
            user_id=self._next_id,
            username=raw_username,
            role=role_value,
            name=ci.name,
            email=ci.email,
            phone_number=ci.phone_number,
            password=pw_serialized,
            token_version=1,
        )
        self._by_username[norm] = rec
        self._by_id[rec.user_id] = rec
        self._next_id += 1
        self.save()
        return rec

    def update_password(self, username: str, new_hash: PasswordHash) -> None:
        """Replace the stored password hash for a user.

        Args:
            username: Username whose password should change.
            new_hash: Replacement password hash.

        Raises:
            ValueError: If the user does not exist.
        """
        norm = self._normalize_username(username)
        rec = self._by_username.get(norm)
        if rec is None:
            raise ValueError("User not found.")
        updated = replace(
            rec,
            password=new_hash.serialize(),
            token_version=rec.token_version + 1,
        )
        self._by_username[norm] = updated
        self._by_id[updated.user_id] = updated
        self.save()

    def save(self) -> None:
        """Persist pending changes.

        The in-memory implementation has no backing store, so this is a no-op.
        """
        return

    def list_users(self) -> list[UserRecord]:
        """Return all persisted user records."""
        return list(self._by_id.values())

    def get_by_id(self, user_id: int) -> UserRecord | None:
        """Return a user by their id, or `None` when absent."""
        return self._by_id.get(user_id)

    def increment_token_version_by_id(self, user_id: int) -> UserRecord | None:
        """Increment a user's token version by id and return the updated record."""
        user = self.get_by_id(user_id)
        if user is None:
            return None

        return self._increment_token_version(user)

    def increment_token_version_by_username(self, username: str) -> UserRecord | None:
        """Increment a user's token version by username and return the updated record."""
        user = self.get_by_username(username)
        if user is None:
            return None

        return self._increment_token_version(user)

    def _increment_token_version(self, user: UserRecord) -> UserRecord:
        """Store and return a copy of the user with token_version incremented."""
        key = self._normalize_username(user.username)
        updated = replace(user, token_version=user.token_version + 1)
        self._by_username[key] = updated
        self._by_id[updated.user_id] = updated
        self.save()
        return updated

    @staticmethod
    def _normalize_role(role: object) -> str:
        """Normalize a role enum or role string into the persisted role value."""
        if isinstance(role, Role):
            return role.value
        if not isinstance(role, str):
            raise TypeError(f"Invalid role: {role!r}")
        try:
            return Role(role.strip().upper()).value
        except ValueError as exc:
            raise ValueError(f"Invalid role: {role!r}") from exc
