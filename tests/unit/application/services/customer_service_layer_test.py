import unittest

from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.application.services.customer_service import CustomerService
from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo


class CustomerServiceLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryCustomerRepository()
        self.service = CustomerService(self.repo)

    def make_customer(self, customer_id: int, name: str, email: str = "", phone: str = "") -> Customer:
        customer = Customer(
            customer_id=customer_id, contact=ContactInfo(name=name, email=email, phone_number=phone)
        )
        self.repo.add(customer)
        return customer

    def test_find_existing_customer_raises_when_email_and_phone_belong_to_different_customers(self) -> None:
        self.make_customer(1, "Alice", email="alice@example.com")
        self.make_customer(2, "Alice", phone="0412345678")

        with self.assertRaises(ValueError) as ctx:
            self.service.find_existing_customer("Alice", "alice@example.com", "0412345678")

        self.assertIn("Email belongs to customer ID: 1", str(ctx.exception))
        self.assertIn("phone belongs to customer ID: 2", str(ctx.exception))

    def test_find_existing_customer_returns_customer_when_email_and_phone_match_same_customer(self) -> None:
        customer = self.make_customer(1, "Alice", email="alice@example.com", phone="0412345678")

        found = self.service.find_existing_customer("  Alice  ", "ALICE@example.com", "04 1234 5678")

        self.assertIs(found, customer)

    def test_find_existing_customer_raises_when_matching_email_customer_has_different_name(self) -> None:
        self.make_customer(1, "Alice", email="alice@example.com")

        with self.assertRaises(ValueError) as ctx:
            self.service.find_existing_customer("Bob", "alice@example.com", "")

        self.assertIn("does not match existing customer ID 1", str(ctx.exception))

    def test_find_existing_customer_returns_phone_match_when_name_matches(self) -> None:
        customer = self.make_customer(1, "Alice", phone="0412345678")

        found = self.service.find_existing_customer("Alice", "", "04 1234 5678")

        self.assertIs(found, customer)

    def test_find_existing_customer_returns_unique_name_only_customer_when_no_contact_info_provided(
        self,
    ) -> None:
        customer = self.make_customer(1, "Alice")

        found = self.service.find_existing_customer(" alice ")

        self.assertIs(found, customer)

    def test_find_existing_customer_returns_none_for_ambiguous_name_only_match(self) -> None:
        self.make_customer(1, "Alice")
        self.make_customer(2, "Alice", email="alice2@example.com")

        found = self.service.find_existing_customer("Alice")

        self.assertIsNone(found)

    def test_find_existing_customer_returns_none_when_no_customer_matches(self) -> None:
        found = self.service.find_existing_customer("Alice", "alice@example.com", "0412345678")

        self.assertIsNone(found)

    def test_create_normalizes_contact_info_and_adds_customer_to_repository(self) -> None:
        created = self.service.create("  Alice  ", "ALICE@example.com", "0412345678")

        self.assertEqual(created.customer_id, 1)
        self.assertEqual(created.name, "Alice")
        self.assertEqual(created.email, "alice@example.com")
        self.assertEqual(created.phone_number, "0412345678")
        self.assertIs(self.repo.get_by_id(1), created)
        self.assertIs(self.repo.get_by_email("alice@example.com"), created)
        self.assertIs(self.repo.get_by_phone("0412345678"), created)


if __name__ == "__main__":
    unittest.main()
