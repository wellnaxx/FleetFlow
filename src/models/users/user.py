from src.models.auth import Role
from src.models.contact_info import ContactInfo

class User:
    _user_id = 1

    def __init__(self, contact: ContactInfo, role: Role):
        self._user_id = User._user_id
        User._user_id += 1
        self.role = role
        self.contact = contact

    @property
    def user_id(self): return self._user_id
    @property
    def name(self): return self.contact.name
    @property
    def email(self): return self.contact.email
    @property
    def phone_number(self): return self.contact.phone_number