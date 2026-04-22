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

    def test_user_properties_and_role(self):
        contact = self.make_contact("Bob", "bob@ex.com", "0412345678")
        u = User(contact, Role.EMPLOYEE)

        self.assertIs(u.contact, contact)  # stored object
        self.assertEqual(u.name, "Bob")  # property proxies
        self.assertEqual(u.email, "bob@ex.com")
        self.assertEqual(u.phone_number, "0412345678")
        self.assertEqual(u.role, Role.EMPLOYEE)

    def test_user_defaults_user_id_to_none(self):
        c1 = self.make_contact("Customer1")
        u1 = User(c1, Role.MANAGER)

        self.assertIsNone(u1.user_id)

    def test_user_preserves_explicit_user_id(self):
        user = User(self.make_contact("Customer1"), Role.EMPLOYEE, user_id=17)

        self.assertEqual(user.user_id, 17)


class Manager_Should(unittest.TestCase):
    def test_is_user_and_role_is_manager(self):
        m = Manager("Alice", "alice@ex.com", "0412345678")
        self.assertIsInstance(m, User)
        self.assertEqual(m.role, Role.MANAGER)

    def test_properties_proxy_contact_info(self):
        m = Manager("Bob", "bob@ex.com", "0400123456")
        self.assertEqual(m.name, "Bob")
        self.assertEqual(m.email, "bob@ex.com")
        self.assertEqual(m.phone_number, "0400123456")

    def test_manager_defaults_user_id_to_none(self):
        m = Manager("Customer1")
        self.assertIsNone(m.user_id)

    def test_manager_preserves_explicit_user_id(self):
        m = Manager("Customer1", user_id=23)
        self.assertEqual(m.user_id, 23)


class Employee_Should(unittest.TestCase):
    def test_is_user_and_role_is_employee(self):
        e = Employee("Alice", "alice@ex.com", "0412345678")
        self.assertIsInstance(e, User)
        self.assertEqual(e.role, Role.EMPLOYEE)

    def test_properties_proxy_contact_info(self):
        e = Employee("Bob", "bob@ex.com", "0400123456")
        self.assertEqual(e.name, "Bob")
        self.assertEqual(e.email, "bob@ex.com")
        self.assertEqual(e.phone_number, "0400123456")

    def test_employee_defaults_user_id_to_none(self):
        e = Employee("Customer1")
        self.assertIsNone(e.user_id)

    def test_employee_preserves_explicit_user_id(self):
        e = Employee("Customer1", user_id=31)
        self.assertEqual(e.user_id, 31)
