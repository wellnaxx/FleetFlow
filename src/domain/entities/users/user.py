from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class User:
    def __init__(self, contact: ContactInfo, role: Role, user_id: int | None = None) -> None:
        self._user_id = user_id
        self.role = role
        self.contact = contact

    @property
    def user_id(self) -> int | None:
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
