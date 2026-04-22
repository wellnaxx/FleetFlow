import json
import logging
import os
import tempfile
from dataclasses import asdict, replace
from typing import Any, cast

from src.adapters.driven.persistence.json.paths import ensure_data_dir, resolve_data_path
from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo

logger = logging.getLogger(__name__)


class UserStore:
    """Load/save users to data/users.json (or a custom path) with atomic writes."""

    def __init__(self, path: str = "users.json") -> None:
        """
        Args:
            path: Filename or path to the users file. Bare filenames are placed in data/.
        """
        self.path: str = resolve_data_path(path)
        self._by_username: dict[str, UserRecord] = {}
        self._next_id: int = 1
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data: object = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed user store JSON: {self.path}") from exc

        try:
            next_id, users_by_username = self._parse_loaded_payload(data)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Malformed user store JSON: {self.path}") from exc

        self._next_id = next_id
        self._by_username = users_by_username

    @staticmethod
    def _parse_loaded_payload(data: object) -> tuple[int, dict[str, UserRecord]]:
        if not isinstance(data, dict):
            raise TypeError("payload must be an object")

        payload = cast(dict[object, object], data)
        next_id = UserStore._parse_next_id(payload)
        if "users" not in payload:
            raise TypeError("'users' is required")
        users_obj = payload["users"]
        if not isinstance(users_obj, list):
            raise TypeError("'users' must be a list")
        users = cast(list[object], users_obj)

        users_by_username: dict[str, UserRecord] = {}
        seen_user_ids: set[int] = set()
        max_user_id = 0
        for raw_user in users:
            user = UserStore._parse_raw_user(raw_user)
            key = user.username.lower()
            if key in users_by_username:
                raise ValueError(f"Duplicate username in store: {user.username!r}")
            user_id = user.user_id
            if user_id in seen_user_ids:
                raise ValueError(f"Duplicate user_id in store: {user_id}")
            seen_user_ids.add(user_id)
            max_user_id = max(max_user_id, user_id)
            users_by_username[key] = user

        corrected_next_id = max(next_id, max_user_id + 1)
        return corrected_next_id, users_by_username

    @staticmethod
    def _parse_next_id(payload: dict[object, object]) -> int:
        next_id = payload.get("_next_id", 1)
        if not isinstance(next_id, int) or isinstance(next_id, bool):
            raise TypeError(f"_next_id must be int, got {type(next_id).__name__}")
        return next_id

    @staticmethod
    def _parse_raw_user(raw_user: object) -> UserRecord:
        if not isinstance(raw_user, dict):
            raise TypeError("user record must be an object")

        raw = cast(dict[object, object], raw_user)
        user_id = raw["user_id"]
        if not isinstance(user_id, int) or isinstance(user_id, bool):
            raise TypeError(f"user_id must be int, got {type(user_id).__name__}")

        username = UserStore._parse_string_field(raw, "username")
        role = UserStore._parse_string_field(raw, "role")
        name = UserStore._parse_string_field(raw, "name")
        email = UserStore._parse_string_field(raw, "email")
        phone_number = UserStore._parse_string_field(raw, "phone_number")
        password = UserStore._parse_string_field(raw, "password")

        return UserRecord(
            user_id=user_id,
            username=username,
            role=role,
            name=name,
            email=email,
            phone_number=phone_number,
            password=password,
        )

    @staticmethod
    def _parse_string_field(raw: dict[object, object], field: str) -> str:
        value = raw[field]
        if not isinstance(value, str):
            raise TypeError(f"{field!r} must be str, got {type(value).__name__}")
        return value

    @staticmethod
    def _normalize_role(role: Role | str) -> str:
        if isinstance(role, Role):
            return role.value
        try:
            return Role(role.upper()).value
        except ValueError as exc:
            raise ValueError(f"Invalid role: {role!r}") from exc

    def _atomic_write(self, data: dict[str, Any]) -> str:
        """Write JSON atomically to self.path. Returns absolute path."""
        ensure_data_dir()
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".users.", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError as exc:
                logger.warning("Failed to remove temporary user store file %r: %s", tmp, exc)
        return self.path

    def save(self) -> str:
        """Persist users to disk. Returns absolute path."""
        data = {
            "_next_id": self._next_id,
            "users": [asdict(rec) for rec in sorted(self._by_username.values(), key=lambda r: r.user_id)],
        }
        return self._atomic_write(data)

    def get(self, username: str) -> UserRecord | None:
        """Fetch a user by username (case-insensitive)."""
        key = (username or "").lower()
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
        """Create and persist a new user. Raises ValueError if username exists."""
        key = username.strip()
        norm = key.lower()
        if not norm:
            raise ValueError("Username is required.")
        if norm in self._by_username:
            raise ValueError("Username already exists.")

        role_value = UserStore._normalize_role(role)

        ci = ContactInfo(name=name, email=email, phone_number=phone_number)
        clean_name = ci.name
        clean_email = ci.email
        clean_phone = ci.phone_number

        try:
            pw_serialized = password_hash.serialize()
        except AttributeError as e:
            raise TypeError("password_hash must be a PasswordHash") from e

        rec = UserRecord(
            user_id=self._next_id,
            username=key,
            role=role_value,
            name=clean_name,
            email=clean_email,
            phone_number=clean_phone,
            password=pw_serialized,
        )

        self._by_username[norm] = rec
        self._next_id += 1
        self.save()
        return rec

    def update_password(self, username: str, new_hash: PasswordHash) -> None:
        """Update the password for an existing user."""
        rec = self.get(username)

        if not rec:
            raise ValueError("User not found.")

        self._by_username[username.lower()] = replace(rec, password=new_hash.serialize())
        self.save()

    def list_users(self) -> list[UserRecord]:
        """Return all users (unordered)."""
        return list(self._by_username.values())
