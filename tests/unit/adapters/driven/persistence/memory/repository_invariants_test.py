import unittest

from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.contact_info import ContactInfo


class InMemoryRepositoryInvariants_Should(unittest.TestCase):
    def test_customer_repository_rejects_duplicate_id(self) -> None:
        repo = InMemoryCustomerRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        repo.add(customer)

        with self.assertRaises(ValueError) as ctx:
            repo.add(Customer(customer_id=1, contact=ContactInfo(name="Bob")))

        self.assertIn("Customer with id 1 already exists.", str(ctx.exception))

    def test_customer_repository_rejects_duplicate_email(self) -> None:
        repo = InMemoryCustomerRepository()
        repo.add(Customer(customer_id=1, contact=ContactInfo(name="Alice", email="alice@example.com")))

        with self.assertRaises(ValueError) as ctx:
            repo.add(Customer(customer_id=2, contact=ContactInfo(name="Bob", email="alice@example.com")))

        self.assertIn("Email already in use", str(ctx.exception))

    def test_customer_repository_rejects_duplicate_phone(self) -> None:
        repo = InMemoryCustomerRepository()
        repo.add(Customer(customer_id=1, contact=ContactInfo(name="Alice", phone_number="0412345678")))

        with self.assertRaises(ValueError) as ctx:
            repo.add(Customer(customer_id=2, contact=ContactInfo(name="Bob", phone_number="0412345678")))

        self.assertIn("Phone already in use", str(ctx.exception))

    def test_package_repository_rejects_duplicate_id(self) -> None:
        repo = InMemoryPackageRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        package = DeliveryPackage("SYD", "MEL", 1.0, customer, 1)
        repo.add(package)

        with self.assertRaises(ValueError) as ctx:
            repo.add(DeliveryPackage("SYD", "MEL", 2.0, customer, 1))

        self.assertIn("Package with id 1 already exists.", str(ctx.exception))

    def test_route_repository_rejects_duplicate_id(self) -> None:
        repo = InMemoryRouteRepository()
        route = DeliveryRoute("SYD", "MEL", route_id=1)
        repo.add(route)

        with self.assertRaises(ValueError) as ctx:
            repo.add(DeliveryRoute("SYD", "MEL", route_id=1))

        self.assertIn("Route with ID 1 already exists", str(ctx.exception))
