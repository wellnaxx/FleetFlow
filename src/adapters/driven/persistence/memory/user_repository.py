from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord
from src.domain.value_objects.contact_info import ContactInfo


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._by_username: dict[str, UserRecord] = {}
        self._next_id = 1

    def get(self, username: str) -> UserRecord | None:
        key = (username or "").strip().lower()
        if not key:
            return None
        return self._by_username.get(key)

    def create(
        self,
        username: str,
        role: str,
        name: str,
        email: str,
        phone_number: str,
        password_hash: PasswordHash,
    ) -> UserRecord:
        key = (username or "").strip()
        norm = key.lower()
        if not norm:
            raise ValueError("Username is required.")
        if norm in self._by_username:
            raise ValueError("Username already exists.")

        role_str: str = getattr(role, "value", role)
        role_value = str(role_str).upper()

        ci = ContactInfo(name=name, email=(email or ""), phone_number=(phone_number or ""))
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
        rec = self.get(username)
        if rec is None:
            raise ValueError("User not found.")
        rec.password = new_hash.serialize()
        self.save()

    def save(self) -> None:
        return None

    def list_users(self) -> list[UserRecord]:
        return list(self._by_username.values())
