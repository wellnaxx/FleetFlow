import unittest
from unittest.mock import patch

from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.contact_info import ContactInfo


class RuntimePackageRemovalIntegrationTests(unittest.TestCase):
    def test_remove_assigned_package_updates_repo_and_route(self) -> None:
        package_repo = InMemoryPackageRepository()
        customer = Customer(
            customer_id=1,
            contact=ContactInfo(name="Alice", email="", phone_number=""),
        )

        with (
            patch("src.domain.entities.delivery_package.Map.is_valid_location", return_value=True),
            patch("src.domain.entities.delivery_route.Map.get_locations", return_value=["A", "B"]),
        ):
            route = DeliveryRoute("A", "B", route_id=1)
            package = DeliveryPackage(
                package_id=1,
                start_location="A",
                end_location="B",
                weight=1.0,
                customer=customer,
            )
            customer.add_package(package)
            route.assign_package(package)
            package_repo.add(package)

        removed = RemovePackageUseCase(package_repo).execute(package.package_id)

        self.assertIs(removed, package)
        self.assertIsNone(package_repo.get_by_id(package.package_id))
        self.assertEqual(route.packages, [])
        self.assertIsNone(package.route)
        self.assertEqual(package.customer.delivery_packages, ())
