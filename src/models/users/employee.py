from src.models.users.user import User
from src.models.auth import Role
from src.models.contact_info import ContactInfo

class Employee(User):
    def __init__(self, name: str, email: str = "", phone_number: str = ""):
        super().__init__(ContactInfo(name=name, email=email, phone_number=phone_number), Role.EMPLOYEE)