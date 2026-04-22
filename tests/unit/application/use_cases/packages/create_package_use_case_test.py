import unittest
from unittest.mock import MagicMock, patch

from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus


class CreatePackageUseCaseLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.customers = MagicMock()
        self.packages = MagicMock()
        self.use_case = CreatePackageUseCase(self.customers, self.packages)

    @patch("src.application.use_cases.packages.create_package.Map.is_valid_location", side_effect=[False])
    def test_execute_raises_for_invalid_start_location(self, mock_is_valid: MagicMock) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute("BAD", "MEL", 10.0, "Alice")

        self.assertIn("Invalid start location: BAD", str(ctx.exception))
        self.customers.find_existing_customer.assert_not_called()
        self.packages.next_id.assert_not_called()
        self.packages.add.assert_not_called()
        self.assertEqual(mock_is_valid.call_count, 1)

    @patch("src.application.use_cases.packages.create_package.Map.is_valid_location", side_effect=[True, False])
    def test_execute_raises_for_invalid_end_location(self, mock_is_valid: MagicMock) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute("SYD", "BAD", 10.0, "Alice")

        self.assertIn("Invalid end location: BAD", str(ctx.exception))
        self.customers.find_existing_customer.assert_not_called()
        self.packages.next_id.assert_not_called()
        self.packages.add.assert_not_called()

    @patch("src.domain.entities.delivery_package.Map.is_valid_location", return_value=True)
    @patch("src.application.use_cases.packages.create_package.Map.is_valid_location", side_effect=[True, True])
    def test_execute_reuses_existing_customer_and_persists_package(
        self, mock_is_valid: MagicMock, _mock_entity_map: MagicMock
    ) -> None:
        customer = MagicMock()
        self.customers.find_existing_customer.return_value = customer
        self.packages.peek_next_id.return_value = 42

        package = self.use_case.execute("SYD", "MEL", 12.5, "Alice", "alice@example.com", "0412345678")

        self.customers.find_existing_customer.assert_called_once_with(
            "Alice", "alice@example.com", "0412345678"
        )
        self.customers.create.assert_not_called()
        self.packages.peek_next_id.assert_called_once_with()
        customer.add_package.assert_called_once_with(package)
        self.packages.add.assert_called_once_with(package)
        self.assertIsInstance(package, DeliveryPackage)
        self.assertEqual(package.package_id, 42)
        self.assertIs(package.customer, customer)
        self.assertEqual(package.status, ItemStatus.TODO)

    @patch("src.domain.entities.delivery_package.Map.is_valid_location", return_value=True)
    @patch("src.application.use_cases.packages.create_package.Map.is_valid_location", side_effect=[True, True])
    def test_execute_creates_customer_when_missing(
        self, mock_is_valid: MagicMock, _mock_entity_map: MagicMock
    ) -> None:
        customer = MagicMock()
        self.customers.find_existing_customer.return_value = None
        self.customers.create.return_value = customer
        self.packages.peek_next_id.return_value = 7

        package = self.use_case.execute("SYD", "MEL", 3.5, "Alice", "alice@example.com", "0412345678")

        self.customers.find_existing_customer.assert_called_once_with(
            "Alice", "alice@example.com", "0412345678"
        )
        self.customers.create.assert_called_once_with("Alice", "alice@example.com", "0412345678")
        self.packages.peek_next_id.assert_called_once_with()
        customer.add_package.assert_called_once_with(package)
        self.packages.add.assert_called_once_with(package)
        self.assertEqual(package.package_id, 7)
        self.assertEqual(package.status, ItemStatus.TODO)


if __name__ == "__main__":
    unittest.main()
