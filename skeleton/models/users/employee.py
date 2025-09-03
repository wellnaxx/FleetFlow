from models.users.user import User

class Employee(User):
    def __init__(self, name, phone_number, email):
        super().__init__(name, phone_number, email)

