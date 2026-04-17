from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class User:
    _user_id: int = 1

    def __init__(self, contact: ContactInfo, role: Role) -> None:
        self._user_id = User._user_id
        User._user_id += 1
        self.role = role
        self.contact = contact

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def name(self) -> str:
        return self.contact.name

    @property
    def email(self) -> str:
        return self.contact.email

    @property
    def phone_number(self) -> str:
        return self.contact.phone_number
