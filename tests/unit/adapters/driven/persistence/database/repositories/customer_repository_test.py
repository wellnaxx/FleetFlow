import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.customer_repository import PostgresCustomerRepository
from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo

MODULE = "src.adapters.driven.persistence.database.repositories.customer_repository"


class PostgresCustomerRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = PostgresCustomerRepository()

    @patch(f"{MODULE}.execute_insert", return_value=42)
    def test_create_inserts_contact_info_and_returns_customer(self, execute_insert_mock: MagicMock) -> None:
        contact = ContactInfo(name=" Alice ", email="ALICE@example.com", phone_number="0412345678")

        customer = self.repo.create(contact)

        execute_insert_mock.assert_called_once_with(
            QUERIES.customers.add,
            ("Alice", "alice@example.com", "0412345678"),
        )
        self.assertEqual(customer.customer_id, 42)
        self.assertIs(customer.contact, contact)

    @patch(f"{MODULE}.execute_write")
    def test_remove_deletes_customer_by_id(self, execute_write_mock: MagicMock) -> None:
        self.repo.remove(7)

        execute_write_mock.assert_called_once_with(QUERIES.customers.remove, (7,))

    @patch(f"{MODULE}.fetch_one", return_value=None)
    @patch(f"{MODULE}.map_customer")
    def test_get_by_id_returns_none_when_customer_is_missing(
        self,
        map_customer_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        customer = self.repo.get_by_id(7)

        self.assertIsNone(customer)
        fetch_one_mock.assert_called_once_with(QUERIES.customers.get_by_id, (7,))
        map_customer_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_one")
    @patch(f"{MODULE}.map_customer")
    def test_get_by_id_maps_existing_customer(
        self,
        map_customer_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        row = {"customer_id": 7, "name": "Alice", "email": "alice@example.com", "phone": "0412345678"}
        expected = Customer(customer_id=7, contact=ContactInfo(name="Alice"))
        fetch_one_mock.return_value = row
        map_customer_mock.return_value = expected

        customer = self.repo.get_by_id(7)

        self.assertIs(customer, expected)
        fetch_one_mock.assert_called_once_with(QUERIES.customers.get_by_id, (7,))
        map_customer_mock.assert_called_once_with(row)

    @patch(f"{MODULE}.fetch_one")
    @patch(f"{MODULE}.map_customer")
    def test_get_by_email_maps_existing_customer(
        self,
        map_customer_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        row = {"customer_id": 7, "name": "Alice", "email": "alice@example.com", "phone": "0412345678"}
        expected = Customer(customer_id=7, contact=ContactInfo(name="Alice"))
        fetch_one_mock.return_value = row
        map_customer_mock.return_value = expected

        customer = self.repo.get_by_email("alice@example.com")

        self.assertIs(customer, expected)
        fetch_one_mock.assert_called_once_with(QUERIES.customers.get_by_email, ("alice@example.com",))
        map_customer_mock.assert_called_once_with(row)

    @patch(f"{MODULE}.fetch_one", return_value=None)
    @patch(f"{MODULE}.map_customer")
    def test_get_by_email_returns_none_when_customer_is_missing(
        self,
        map_customer_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        customer = self.repo.get_by_email("missing@example.com")

        self.assertIsNone(customer)
        fetch_one_mock.assert_called_once_with(QUERIES.customers.get_by_email, ("missing@example.com",))
        map_customer_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_one")
    @patch(f"{MODULE}.map_customer")
    def test_get_by_phone_maps_existing_customer(
        self,
        map_customer_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        row = {"customer_id": 7, "name": "Alice", "email": "alice@example.com", "phone": "0412345678"}
        expected = Customer(customer_id=7, contact=ContactInfo(name="Alice"))
        fetch_one_mock.return_value = row
        map_customer_mock.return_value = expected

        customer = self.repo.get_by_phone("0412345678")

        self.assertIs(customer, expected)
        fetch_one_mock.assert_called_once_with(QUERIES.customers.get_by_phone, ("0412345678",))
        map_customer_mock.assert_called_once_with(row)

    @patch(f"{MODULE}.fetch_one", return_value=None)
    @patch(f"{MODULE}.map_customer")
    def test_get_by_phone_returns_none_when_customer_is_missing(
        self,
        map_customer_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        customer = self.repo.get_by_phone("0412345678")

        self.assertIsNone(customer)
        fetch_one_mock.assert_called_once_with(QUERIES.customers.get_by_phone, ("0412345678",))
        map_customer_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_customer")
    def test_list_by_name_normalizes_name_and_maps_rows(
        self,
        map_customer_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        rows = [
            {"customer_id": 1, "name": "Alice", "email": "", "phone": ""},
            {"customer_id": 2, "name": "Alice", "email": "alice@example.com", "phone": ""},
        ]
        customers = [
            Customer(customer_id=1, contact=ContactInfo(name="Alice")),
            Customer(customer_id=2, contact=ContactInfo(name="Alice", email="alice@example.com")),
        ]
        fetch_all_mock.return_value = rows
        map_customer_mock.side_effect = customers

        result = self.repo.list_by_name("  ALICE  ")

        self.assertEqual(result, customers)
        fetch_all_mock.assert_called_once_with(QUERIES.customers.list_by_name, ("alice",))
        self.assertEqual([call.args[0] for call in map_customer_mock.call_args_list], rows)

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_customer")
    def test_list_all_maps_all_rows(
        self,
        map_customer_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        rows = [
            {"customer_id": 1, "name": "Alice", "email": "", "phone": ""},
            {"customer_id": 2, "name": "Bob", "email": "", "phone": "0412345678"},
        ]
        customers = [
            Customer(customer_id=1, contact=ContactInfo(name="Alice")),
            Customer(customer_id=2, contact=ContactInfo(name="Bob", phone_number="0412345678")),
        ]
        fetch_all_mock.return_value = rows
        map_customer_mock.side_effect = customers

        result = self.repo.list_all()

        self.assertEqual(result, customers)
        fetch_all_mock.assert_called_once_with(QUERIES.customers.list_all)
        self.assertEqual([call.args[0] for call in map_customer_mock.call_args_list], rows)
