"""Manager runtime user entity."""

from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class Manager(User):
    """Runtime user with manager permissions."""

    def __init__(self, user_id: int, name: str, email: str = "", phone_number: str = "") -> None:
        """Create a manager user.

        Args:
            user_id: Stable persisted user id.
            name: Manager display name.
            email: Optional email address.
            phone_number: Optional phone number.
        """
        super().__init__(ContactInfo(name=name, email=email, phone_number=phone_number), Role.MANAGER, user_id)
