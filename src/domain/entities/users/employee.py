"""Employee runtime user entity."""

from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class Employee(User):
    """Runtime user with employee permissions."""

    def __init__(
        self,
        user_id: int,
        name: str,
        email: str = "",
        phone_number: str = "",
    ) -> None:
        """Create an employee user.

        Args:
            user_id: Stable persisted user id.
            name: Employee display name.
            email: Optional email address.
            phone_number: Optional phone number.
        """
        super().__init__(ContactInfo(name=name, email=email, phone_number=phone_number), Role.EMPLOYEE, user_id)
