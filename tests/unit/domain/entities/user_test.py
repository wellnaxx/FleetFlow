import unittest

from src.domain.entities.user import User
from src.domain.enums.auth import Role
from src.domain.value_objects.contact_info import ContactInfo


class User_Should(unittest.TestCase):
    def make_contact(
        self,
        name: str = "Alice",
        email: str = "a@x.com",
        phone: str = "0400123456",
    ) -> ContactInfo:
        return ContactInfo(name=name, email=email, phone_number=phone)

    def test_properties_proxy_contact_info(self) -> None:
        contact = self.make_contact("Bob", "bob@ex.com", "0412345678")
        user = User(contact, Role.EMPLOYEE, user_id=17)

        self.assertIs(user.contact, contact)
        self.assertEqual(user.name, "Bob")
        self.assertEqual(user.email, "bob@ex.com")
        self.assertEqual(user.phone_number, "0412345678")

    def test_preserves_explicit_user_id(self) -> None:
        user = User(self.make_contact("Customer1"), Role.MANAGER, user_id=42)

        self.assertEqual(user.user_id, 42)

    def test_accepts_each_authorization_role(self) -> None:
        for role in Role:
            with self.subTest(role=role):
                user = User(self.make_contact(), role, user_id=23)

                self.assertEqual(user.role, role)
