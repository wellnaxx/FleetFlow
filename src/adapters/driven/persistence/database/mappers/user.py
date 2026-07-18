"""Database row mappers for user records."""

from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.application.models.user_record import UserRecord
from src.shared.validation import require_int, require_positive_int, require_str


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
    user_id = require_int(row["user_id"], "user_id")
    username = require_str(row["username"], "username")
    role = require_str(row["role"], "role")
    name = require_str(row["name"], "name")
    email = require_str(row["email"], "email")
    phone_number = require_str(row["phone"], "phone")
    password_hash = require_str(row["password_hash"], "password_hash")
    try:
        token_version = require_positive_int(row["token_version"], "token_version")
    except ValueError as exc:
        raise ValueError("token_version must be positive") from exc

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
