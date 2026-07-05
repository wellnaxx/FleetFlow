"""Helpers for hydrating current-user principals from persisted auth records."""

from src.application.exceptions.application_errors import ValidationError
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.models.user_record import UserRecord
from src.domain.enums.auth import Role
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.contact_info import ContactInfo


def create_runtime_authenticated_user_from_record(record: UserRecord) -> CurrentUserPrincipal:
    """Convert a persisted user record into an authenticated principal.

    Args:
        record: Persisted auth user record.

    Returns:
        Current-user principal carrying actor identity and role.

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
        raise ValidationError(f"Invalid persisted role for user {record.username!r}: {record.role!r}") from exc

    return CurrentUserPrincipal(
        user_id=record.user_id,
        username=record.username,
        name=contact.name,
        email=contact.email,
        phone_number=contact.phone_number,
        role=role,
    )
