from dataclasses import replace

from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class InMemoryUserRepository:
    """In-memory user repository keyed by normalized username.

    User ids use a create-time allocation model: `create()` assigns and commits
    the next id directly. Unlike the customer/package/route repos, this
    repository does not expose a peek-then-add id workflow.
    """

    def __init__(self) -> None:
        self._by_username: dict[str, UserRecord] = {}
        self._next_id = 1

    @staticmethod
    def _normalize_username(username: str | None) -> str:
        return (username or "").strip().lower()

    def get(self, username: str) -> UserRecord | None:
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
        raw_username = (username or "").strip()
        norm = self._normalize_username(username)

        if not norm:
            raise ValueError("Username is required.")
        if norm in self._by_username:
            raise ValueError("Username already exists.")

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
        )
        self._by_username[norm] = rec
        self._next_id += 1
        self.save()
        return rec

    def update_password(self, username: str, new_hash: PasswordHash) -> None:
        norm = self._normalize_username(username)
        rec = self._by_username.get(norm)
        if rec is None:
            raise ValueError("User not found.")
        self._by_username[norm] = replace(rec, password=new_hash.serialize())
        self.save()

    def save(self) -> None:
        return None

    def list_users(self) -> list[UserRecord]:
        return list(self._by_username.values())

    @staticmethod
    def _normalize_role(role: Role | str) -> str:
        """Normalize a role enum or role string into the persisted role value."""
        if isinstance(role, Role):
            return role.value
        try:
            return Role(role.upper()).value
        except ValueError as exc:
            raise ValueError(f"Invalid role: {role!r}") from exc
