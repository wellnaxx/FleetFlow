"""Helpers for hydrating runtime user entities from persisted auth records."""

from src.application.exceptions.application_errors import UnsupportedRoleError, ValidationError
from src.application.models.user_record import UserRecord
from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager
from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.contact_info import ContactInfo


def create_runtime_user_from_record(record: UserRecord) -> User:
    """Convert a persisted user record into the matching runtime user entity.

    Args:
        record: Persisted auth user record.

    Returns:
        A `Manager` or `Employee` runtime user.

    Raises:
        ValidationError: If persisted contact or role data is invalid.
    """
    try:
        contact = ContactInfo(
            name=record.name,
            email=record.email,
            phone_number=record.phone_number,
        )
    except DomainValidationError as exc:
        raise ValidationError(str(exc)) from exc

    try:
        role = Role(record.role)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid persisted role for user {record.username!r}: {record.role!r}"
        ) from exc

    if role is Role.MANAGER:
        return Manager(record.user_id, contact.name, contact.email, contact.phone_number)
    if role is Role.EMPLOYEE:
        return Employee(record.user_id, contact.name, contact.email, contact.phone_number)

    raise UnsupportedRoleError(f"Unsupported role: {role}")
