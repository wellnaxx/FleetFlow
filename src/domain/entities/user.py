"""Runtime user entity."""

from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class User:
    """Authenticated user whose role determines authorization capabilities."""

    def __init__(self, contact: ContactInfo, role: Role, user_id: int) -> None:
        """Create a runtime user entity.

        Args:
            contact: Validated user contact details.
            role: Runtime authorization role.
            user_id: Stable persisted user id.
        """
        self._user_id = user_id
        self.role = role
        self.contact = contact

    @property
    def user_id(self) -> int:
        """Stable runtime user identifier."""
        return self._user_id

    @property
    def name(self) -> str:
        """User display name."""
        return self.contact.name

    @property
    def email(self) -> str:
        """Normalized user email address, or an empty string."""
        return self.contact.email

    @property
    def phone_number(self) -> str:
        """Normalized user phone number, or an empty string."""
        return self.contact.phone_number
