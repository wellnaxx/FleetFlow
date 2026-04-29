import unittest
from collections.abc import Callable
from unittest.mock import MagicMock, patch

from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus
from src.domain.value_objects.location_code import LocationCode


def package_factory(
    package_id: int,
) -> Callable[[LocationCode, LocationCode, float, Customer], DeliveryPackage]:
    def create(
        start_location: LocationCode,
        end_location: LocationCode,
        weight: float,
        customer: Customer,
    ) -> DeliveryPackage:
        return DeliveryPackage(
            start_location=start_location,
            end_location=end_location,
            weight=weight,
            customer=customer,
            package_id=package_id,
        )

    return create


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
        self.packages.create.assert_not_called()
        self.assertEqual(mock_is_valid.call_count, 1)

    @patch("src.application.use_cases.packages.create_package.Map.is_valid_location", side_effect=[True, False])
    def test_execute_raises_for_invalid_end_location(self, mock_is_valid: MagicMock) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute("SYD", "BAD", 10.0, "Alice")

        self.assertIn("Invalid end location: BAD", str(ctx.exception))
        self.customers.find_existing_customer.assert_not_called()
        self.packages.create.assert_not_called()

    @patch("src.domain.entities.delivery_package.Map.is_valid_location", return_value=True)
    @patch("src.application.use_cases.packages.create_package.Map.is_valid_location", side_effect=[True, True])
    def test_execute_reuses_existing_customer_and_persists_package(
        self, mock_is_valid: MagicMock, _mock_entity_map: MagicMock
    ) -> None:
        customer = MagicMock()
        self.customers.find_existing_customer.return_value = customer
        self.packages.create.side_effect = package_factory(42)

        package = self.use_case.execute("SYD", "MEL", 12.5, "Alice", "alice@example.com", "0412345678")

        self.customers.find_existing_customer.assert_called_once_with(
            "Alice", "alice@example.com", "0412345678"
        )
        self.customers.create.assert_not_called()
        self.packages.create.assert_called_once_with(
            start_location=LocationCode("SYD"),
            end_location=LocationCode("MEL"),
            weight=12.5,
            customer=customer,
        )
        customer.add_package.assert_called_once_with(package)
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
        self.packages.create.side_effect = package_factory(7)

        package = self.use_case.execute("SYD", "MEL", 3.5, "Alice", "alice@example.com", "0412345678")

        self.customers.find_existing_customer.assert_called_once_with(
            "Alice", "alice@example.com", "0412345678"
        )
        self.customers.create.assert_called_once_with("Alice", "alice@example.com", "0412345678")
        self.packages.create.assert_called_once_with(
            start_location=LocationCode("SYD"),
            end_location=LocationCode("MEL"),
            weight=3.5,
            customer=customer,
        )
        customer.add_package.assert_called_once_with(package)
        self.assertEqual(package.package_id, 7)
        self.assertEqual(package.status, ItemStatus.TODO)


if __name__ == "__main__":
    unittest.main()
