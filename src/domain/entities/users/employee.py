from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class Employee(User):
    def __init__(
        self,
        user_id: int,
        name: str,
        email: str = "",
        phone_number: str = "",
    ) -> None:
        super().__init__(ContactInfo(name=name, email=email, phone_number=phone_number), Role.EMPLOYEE, user_id)
