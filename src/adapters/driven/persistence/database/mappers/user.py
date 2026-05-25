"""Database row mappers for user records."""

from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.application.models.user_record import UserRecord


class UserRecordRow(TypedDict):
    user_id: int
    username: str
    role: str
    name: str
    email: str
    phone: str
    password_hash: str
    token_version: int


def map_user_record(row: RowDict) -> UserRecord:
    """Map a database user row to a UserRecord.

    The password hash is preserved on UserRecord for AuthService.
    The User session entity is constructed by AuthService after credential
    verification, not here.

    Args:
        row: Typed database row for a user.

    Returns:
        UserRecord carrying contact info, role, and password hash.

    Raises:
        KeyError: If a required user column is missing.
        TypeError: If a required user column has an unexpected type.
        ValueError: If the token_version is not positive.
    """
    typed = _as_user_record_row(row)
    return UserRecord(
        user_id=typed["user_id"],
        username=typed["username"],
        role=typed["role"],
        name=typed["name"],
        email=typed["email"],
        phone_number=typed["phone"],
        password=typed["password_hash"],
        token_version=typed["token_version"],
    )


def _as_user_record_row(row: RowDict) -> UserRecordRow:
    """Validate and narrow a generic database row to a user record row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed user record row with validated field types.

    Raises:
        KeyError: If a required user column is missing.
        TypeError: If a required user column has an unexpected type.
        ValueError: If the token_version is not positive.
    """
    user_id = row["user_id"]
    username = row["username"]
    role = row["role"]
    name = row["name"]
    email = row["email"]
    phone_number = row["phone"]
    password_hash = row["password_hash"]
    token_version = row["token_version"]

    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise TypeError(f"user_id: expected int, got {type(user_id).__name__}")
    if not isinstance(username, str):
        raise TypeError(f"username: expected str, got {type(username).__name__}")
    if not isinstance(role, str):
        raise TypeError(f"role: expected str, got {type(role).__name__}")
    if not isinstance(name, str):
        raise TypeError(f"name: expected str, got {type(name).__name__}")
    if not isinstance(email, str):
        raise TypeError(f"email: expected str, got {type(email).__name__}")
    if not isinstance(phone_number, str):
        raise TypeError(f"phone: expected str, got {type(phone_number).__name__}")
    if not isinstance(password_hash, str):
        raise TypeError(f"password_hash: expected str, got {type(password_hash).__name__}")
    if not isinstance(token_version, int) or isinstance(token_version, bool):
        raise TypeError(f"token_version: expected int, got {type(token_version).__name__}")
    if token_version < 1:
        raise ValueError("token_version must be positive")

    return UserRecordRow(
        user_id=user_id,
        username=username,
        role=role,
        name=name,
        email=email,
        phone=phone_number,
        password_hash=password_hash,
        token_version=token_version,
    )
