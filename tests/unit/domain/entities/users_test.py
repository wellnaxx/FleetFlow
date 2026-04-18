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

    def test_user_id_increments_sequentially(self):
        # Create two users in this test and ensure sequential IDs.
        c1 = self.make_contact("Customer1")
        c2 = self.make_contact("Customer2")
        u1 = User(c1, Role.MANAGER)
        u2 = User(c2, Role.EMPLOYEE)

        self.assertIsInstance(u1.user_id, int)
        self.assertIsInstance(u2.user_id, int)
        self.assertEqual(u2.user_id, u1.user_id + 1)

    def test_multiple_users_keep_incrementing(self):
        # Create a few to ensure monotonic growth within test scope.
        ids: list[int] = []
        for i in range(5):
            u = User(self.make_contact(f"Name{i}"), Role.EMPLOYEE)
            ids.append(u.user_id)
        # strictly increasing
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(set(ids)), len(ids))


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

    def test_user_id_increments_sequentially_for_managers(self):
        m1 = Manager("Customer1")
        m2 = Manager("Customer2")
        self.assertIsInstance(m1.user_id, int)
        self.assertIsInstance(m2.user_id, int)
        self.assertEqual(m2.user_id, m1.user_id + 1)


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

    def test_user_id_increments_sequentially_for_employees(self):
        e1 = Employee("Customer1")
        e2 = Employee("Customer2")
        self.assertIsInstance(e1.user_id, int)
        self.assertIsInstance(e2.user_id, int)
        self.assertEqual(e2.user_id, e1.user_id + 1)
