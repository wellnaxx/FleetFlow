"""Helpers for hydrating runtime user entities from persisted auth records."""

from src.application.models.user_record import UserRecord
from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager
from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


def create_runtime_user_from_record(record: UserRecord) -> User:
    """Convert a persisted user record into the matching runtime user entity.

    Args:
        record: Persisted auth user record.

    Returns:
        A `Manager` or `Employee` runtime user.

    Raises:
        ValueError: If the persisted role is invalid or unsupported.
    """
    contact = ContactInfo(
        name=record.name,
        email=record.email,
        phone_number=record.phone_number,
    )

    try:
        role = Role(record.role)
    except ValueError as exc:
        raise ValueError(f"Invalid persisted role for user {record.username!r}: {record.role!r}") from exc

    if role is Role.MANAGER:
        return Manager(record.user_id, contact.name, contact.email, contact.phone_number)
    if role is Role.EMPLOYEE:
        return Employee(record.user_id, contact.name, contact.email, contact.phone_number)

    raise ValueError(f"Unsupported role: {role}")
