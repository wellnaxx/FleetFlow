import unittest

from src.adapters.driven.persistence.application_data.customer_repository import (
    ApplicationDataCustomerRepository,
)
from src.core.application_data import ApplicationData
from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo


class ApplicationDataCustomerRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app_data = ApplicationData(current_user=None)
        self.repo = ApplicationDataCustomerRepository(self.app_data)

    @staticmethod
    def make_customer(customer_id: int, name: str, email: str = "", phone: str = "") -> Customer:
        return Customer(
            customer_id=customer_id, contact=ContactInfo(name=name, email=email, phone_number=phone)
        )

    def test_next_id_uses_application_data_allocator(self) -> None:
        self.assertEqual(self.repo.next_id(), 1)
        self.assertEqual(self.repo.next_id(), 2)

    def test_add_stores_customer_in_list_and_indexes(self) -> None:
        customer = self.make_customer(1, "Alice", "alice@example.com", "0412345678")

        self.repo.add(customer)

        self.assertEqual(self.app_data.customer_store, [customer])
        self.assertIs(self.app_data.customer_email_store["alice@example.com"], customer)
        self.assertIs(self.app_data.customer_phone_store["0412345678"], customer)

    def test_add_raises_for_duplicate_customer_id(self) -> None:
        customer = self.make_customer(1, "Alice")
        self.repo.add(customer)

        with self.assertRaises(ValueError) as ctx:
            self.repo.add(self.make_customer(1, "Bob"))

        self.assertIn("Customer with id 1 already exists.", str(ctx.exception))

    def test_remove_deletes_customer_from_list_and_indexes(self) -> None:
        customer = self.make_customer(1, "Alice", "alice@example.com", "0412345678")
        self.repo.add(customer)

        self.repo.remove(1)

        self.assertEqual(self.app_data.customer_store, [])
        self.assertNotIn("alice@example.com", self.app_data.customer_email_store)
        self.assertNotIn("0412345678", self.app_data.customer_phone_store)

    def test_getters_and_list_methods_return_expected_customers(self) -> None:
        alice = self.make_customer(1, "Alice", "alice@example.com", "0412345678")
        bob = self.make_customer(2, "Bob", "bob@example.com", "0499999999")
        self.repo.add(alice)
        self.repo.add(bob)

        self.assertIs(self.repo.get_by_id(1), alice)
        self.assertIsNone(self.repo.get_by_id(999))
        self.assertIs(self.repo.get_by_email("alice@example.com"), alice)
        self.assertIsNone(self.repo.get_by_email(""))
        self.assertIs(self.repo.get_by_phone("0499999999"), bob)
        self.assertIsNone(self.repo.get_by_phone(""))
        self.assertEqual(self.repo.list_by_name(" alice "), [alice])
        self.assertEqual(self.repo.list_all(), [alice, bob])


if __name__ == "__main__":
    unittest.main()
