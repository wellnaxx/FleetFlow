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

    def test_customer_repository_rebuilds_indexes_and_counter_on_replace(self) -> None:
        repo = InMemoryCustomerRepository()
        alice = Customer(
            customer_id=2,
            contact=ContactInfo(name="Alice", email="alice@example.com", phone_number="0412345678"),
        )
        bob = Customer(customer_id=1, contact=ContactInfo(name="Bob"))

        repo.replace_customers({alice.customer_id: alice, bob.customer_id: bob}, next_id=7)

        self.assertEqual(repo.next_id(), 7)
        self.assertEqual([customer.customer_id for customer in repo.list_all()], [1, 2])
        self.assertIs(repo.get_by_email("alice@example.com"), alice)
        self.assertIs(repo.get_by_phone("0412345678"), alice)
        self.assertEqual(repo.list_by_name("bob"), [bob])

    def test_package_repository_rejects_duplicate_id(self) -> None:
        repo = InMemoryPackageRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        package = DeliveryPackage("SYD", "MEL", 1.0, customer, 1)
        repo.add(package)

        with self.assertRaises(ValueError) as ctx:
            repo.add(DeliveryPackage("SYD", "MEL", 2.0, customer, 1))

        self.assertIn("Package with id 1 already exists.", str(ctx.exception))

    def test_package_repository_tracks_counter_and_lists_unassigned_in_id_order(self) -> None:
        repo = InMemoryPackageRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        assigned_route = DeliveryRoute("SYD", "MEL", route_id=9)
        assigned = DeliveryPackage("SYD", "MEL", 1.0, customer, 2)
        assigned.route = assigned_route
        unassigned = DeliveryPackage("SYD", "ADL", 2.0, customer, 1)

        repo.add(assigned)
        repo.add(unassigned)

        self.assertEqual(repo.next_id(), 3)
        self.assertEqual([package.package_id for package in repo.list_all()], [1, 2])
        self.assertEqual([package.package_id for package in repo.list_unassigned()], [1])

    def test_package_repository_replaces_packages_and_counter(self) -> None:
        repo = InMemoryPackageRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        package = DeliveryPackage("SYD", "MEL", 1.0, customer, 4)

        repo.replace_packages({4: package}, next_id=8)

        self.assertEqual(repo.next_id(), 8)
        self.assertIs(repo.get_by_id(4), package)

    def test_route_repository_rejects_duplicate_id(self) -> None:
        repo = InMemoryRouteRepository()
        route = DeliveryRoute("SYD", "MEL", route_id=1)
        repo.add(route)

        with self.assertRaises(ValueError) as ctx:
            repo.add(DeliveryRoute("SYD", "MEL", route_id=1))

        self.assertIn("Route with ID 1 already exists", str(ctx.exception))

    def test_route_repository_tracks_counter_and_lists_routes_in_id_order(self) -> None:
        repo = InMemoryRouteRepository()
        route_b = DeliveryRoute("SYD", "MEL", route_id=2)
        route_a = DeliveryRoute("SYD", "ADL", route_id=1)

        repo.add(route_b)
        repo.add(route_a)

        self.assertEqual(repo.next_id(), 3)
        self.assertEqual([route.route_id for route in repo.list_all()], [1, 2])

    def test_route_repository_replaces_routes_and_counter(self) -> None:
        repo = InMemoryRouteRepository()
        route = DeliveryRoute("SYD", "MEL", route_id=5)

        repo.replace_routes({5: route}, next_id=9)

        self.assertEqual(repo.next_id(), 9)
        self.assertIs(repo.get_by_id(5), route)
