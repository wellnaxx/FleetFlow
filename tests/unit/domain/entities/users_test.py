import unittest

from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager
from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class User_Should(unittest.TestCase):
    def make_contact(
        self, name: str = "Alice", email: str = "a@x.com", phone: str = "0400123456"
    ) -> ContactInfo:
        return ContactInfo(name=name, email=email, phone_number=phone)

    def test_user_properties_role_and_user_id(self) -> None:
        contact = self.make_contact("Bob", "bob@ex.com", "0412345678")
        user = User(contact, Role.EMPLOYEE, user_id=17)

        self.assertIs(user.contact, contact)
        self.assertEqual(user.name, "Bob")
        self.assertEqual(user.email, "bob@ex.com")
        self.assertEqual(user.phone_number, "0412345678")
        self.assertEqual(user.role, Role.EMPLOYEE)
        self.assertEqual(user.user_id, 17)

    def test_user_preserves_explicit_user_id(self) -> None:
        user = User(self.make_contact("Customer1"), Role.MANAGER, user_id=42)

        self.assertEqual(user.user_id, 42)


class Manager_Should(unittest.TestCase):
    def test_is_user_and_role_is_manager(self) -> None:
        manager = Manager(23, "Alice", "alice@ex.com", "0412345678")

        self.assertIsInstance(manager, User)
        self.assertEqual(manager.role, Role.MANAGER)
        self.assertEqual(manager.user_id, 23)

    def test_properties_proxy_contact_info(self) -> None:
        manager = Manager(24, "Bob", "bob@ex.com", "0400123456")

        self.assertEqual(manager.name, "Bob")
        self.assertEqual(manager.email, "bob@ex.com")
        self.assertEqual(manager.phone_number, "0400123456")
        self.assertEqual(manager.user_id, 24)

    def test_manager_preserves_explicit_user_id(self) -> None:
        manager = Manager(25, "Customer1")

        self.assertEqual(manager.user_id, 25)


class Employee_Should(unittest.TestCase):
    def test_is_user_and_role_is_employee(self) -> None:
        employee = Employee(31, "Alice", "alice@ex.com", "0412345678")

        self.assertIsInstance(employee, User)
        self.assertEqual(employee.role, Role.EMPLOYEE)
        self.assertEqual(employee.user_id, 31)

    def test_properties_proxy_contact_info(self) -> None:
        employee = Employee(32, "Bob", "bob@ex.com", "0400123456")

        self.assertEqual(employee.name, "Bob")
        self.assertEqual(employee.email, "bob@ex.com")
        self.assertEqual(employee.phone_number, "0400123456")
        self.assertEqual(employee.user_id, 32)

    def test_employee_preserves_explicit_user_id(self) -> None:
        employee = Employee(33, "Customer1")

        self.assertEqual(employee.user_id, 33)
