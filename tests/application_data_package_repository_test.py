import unittest
from unittest.mock import patch

from src.adapters.driven.persistence.application_data.package_repository import ApplicationDataPackageRepository
from src.core.application_data import ApplicationData
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.value_objects.contact_info import ContactInfo


class ApplicationDataPackageRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app_data = ApplicationData(current_user=None)
        self.repo = ApplicationDataPackageRepository(self.app_data)
        self.customer = Customer(
            customer_id=1,
            contact=ContactInfo(name="Alice", email="alice@example.com", phone_number="0412345678"),
        )

    def make_package(self, package_id: int, *, assigned: bool = False) -> DeliveryPackage:
        with patch("src.domain.entities.delivery_package.Map.is_valid_location", return_value=True):
            package = DeliveryPackage("SYD", "MEL", 10.0, self.customer, package_id)
        if assigned:
            package.route = object()  # type: ignore[assignment]
        return package

    def test_next_id_uses_application_data_allocator(self) -> None:
        self.assertEqual(self.repo.next_id(), 1)
        self.assertEqual(self.repo.next_id(), 2)

    def test_add_stores_package_and_duplicate_id_raises(self) -> None:
        package = self.make_package(1)
        self.repo.add(package)

        self.assertEqual(self.app_data.package_store, [package])

        with self.assertRaises(ValueError) as ctx:
            self.repo.add(self.make_package(1))

        self.assertIn("Package with id 1 already exists.", str(ctx.exception))

    def test_remove_deletes_package_from_store(self) -> None:
        package = self.make_package(1)
        self.repo.add(package)

        self.repo.remove(1)

        self.assertEqual(self.app_data.package_store, [])

    def test_get_by_id_and_list_all_return_expected_values(self) -> None:
        package1 = self.make_package(1)
        package2 = self.make_package(2)
        self.repo.add(package1)
        self.repo.add(package2)

        self.assertIs(self.repo.get_by_id(1), package1)
        self.assertIsNone(self.repo.get_by_id(999))
        self.assertEqual(self.repo.list_all(), [package1, package2])

    def test_list_unassigned_filters_out_assigned_packages(self) -> None:
        unassigned = self.make_package(1, assigned=False)
        assigned = self.make_package(2, assigned=True)
        self.repo.add(unassigned)
        self.repo.add(assigned)

        self.assertEqual(self.repo.list_unassigned(), [unassigned])


if __name__ == "__main__":
    unittest.main()
