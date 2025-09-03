from models.users.employee import Employee

class Manager(Employee):
    def __init__(self, name, phone_number, email):
        super().__init__(name, phone_number, email)