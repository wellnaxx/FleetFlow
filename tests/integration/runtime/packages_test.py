import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.unit_of_work import InMemoryUnitOfWork
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.item_status import ItemStatus
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode
from tests.unit.application.use_cases.authz_helpers import manager_authz


class RuntimePackageRemovalIntegrationTests(unittest.TestCase):
    def test_remove_assigned_package_updates_repo_route_and_package_state(self) -> None:
        package_repo = InMemoryPackageRepository()
        customer = Customer(
            customer_id=1,
            contact=ContactInfo(name="Alice", email="", phone_number=""),
        )

        with (
            patch("src.domain.entities.delivery_package.Map.is_valid_location", return_value=True),
            patch(
                "src.domain.entities.delivery_route.Map.get_locations",
                return_value=[LocationCode("A"), LocationCode("B")],
            ),
            patch("src.domain.entities.delivery_route.Map.get_distance", return_value=100),
        ):
            route = DeliveryRoute(LocationCode("A"), LocationCode("B"), route_id=1)
            package = DeliveryPackage.create(
                package_id=1,
                start_location=LocationCode("A"),
                end_location=LocationCode("B"),
                weight=1.0,
                customer=customer,
            )

            customer.add_package(package)
            route.assign_package(package, occurred_at=datetime(2025, 1, 1, 8, 0))
            package_repo.add(package)

        unit_of_work = InMemoryUnitOfWork(routes=MagicMock(), packages=package_repo, trucks=MagicMock())
        result = RemovePackageUseCase(
            package_repo,
            unit_of_work,
            manager_authz(),
        ).execute(package.package_id)

        self.assertIs(result.package, package)
        self.assertIs(result.customer, customer)
        self.assertIs(result.route, route)
        self.assertIsNone(package_repo.get_by_id(package.package_id))

        self.assertEqual(route.packages, ())
        self.assertIsNone(package.route)
        self.assertIsNone(package.expected_arrival)
        self.assertEqual(package.status, ItemStatus.TODO)
        self.assertEqual(package.current_location, LocationCode("A"))

        self.assertEqual(customer.delivery_packages, ())
        self.assertIs(package.customer, customer)
