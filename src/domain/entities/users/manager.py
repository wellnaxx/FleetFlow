from domain.entities.users.user import User
from domain.enums.auth import Role
from domain.value_objects.contact_info import ContactInfo


class Manager(User):
    def __init__(self, name: str, email: str = "", phone_number: str = "") -> None:
        super().__init__(ContactInfo(name=name, email=email, phone_number=phone_number), Role.MANAGER)
