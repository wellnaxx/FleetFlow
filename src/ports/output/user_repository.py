from typing import Protocol

from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord


class UserRepositoryPort(Protocol):
    def get(self, username: str) -> UserRecord | None: ...
    def create(
        self,
        username: str,
        role: str,
        name: str,
        email: str,
        phone_number: str,
        password_hash: PasswordHash,
    ) -> UserRecord: ...
    def update_password(self, username: str, new_hash: PasswordHash) -> None: ...
    def save(self) -> str | None: ...
    def list_users(self) -> list[UserRecord]: ...
