import unittest

from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode


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

        self.assertEqual(repo.peek_next_id(), 7)
        self.assertEqual([customer.customer_id for customer in repo.list_all()], [1, 2])
        self.assertIs(repo.get_by_email("alice@example.com"), alice)
        self.assertIs(repo.get_by_phone("0412345678"), alice)
        self.assertEqual(repo.list_by_name("bob"), [bob])

    def test_customer_repository_lists_pages_and_counts_customers(self) -> None:
        repo = InMemoryCustomerRepository()
        alice = Customer(customer_id=2, contact=ContactInfo(name="Alice"))
        bob = Customer(customer_id=1, contact=ContactInfo(name="Bob"))
        carol = Customer(customer_id=3, contact=ContactInfo(name="Carol"))

        repo.add(alice)
        repo.add(bob)
        repo.add(carol)

        self.assertEqual([customer.customer_id for customer in repo.list_page(limit=2, offset=1)], [2, 3])
        page, total = repo.list_page_with_total(limit=2, offset=1)
        self.assertEqual([customer.customer_id for customer in page], [2, 3])
        self.assertEqual(total, 3)
        self.assertEqual(repo.count_all(), 3)

    def test_package_repository_rejects_duplicate_id(self) -> None:
        repo = InMemoryPackageRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        package = DeliveryPackage(
            LocationCode("SYD"),
            LocationCode("MEL"),
            1.0,
            customer,
            1,
        )
        repo.add(package)

        with self.assertRaises(ValueError) as ctx:
            repo.add(
                DeliveryPackage(
                    LocationCode("SYD"),
                    LocationCode("MEL"),
                    2.0,
                    customer,
                    1,
                )
            )

        self.assertIn("Package with id 1 already exists.", str(ctx.exception))

    def test_package_repository_tracks_counter_and_lists_unassigned_in_id_order(self) -> None:
        repo = InMemoryPackageRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        assigned_route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=9)
        assigned = DeliveryPackage(
            LocationCode("SYD"),
            LocationCode("MEL"),
            1.0,
            customer,
            2,
        )
        assigned.route = assigned_route
        unassigned = DeliveryPackage(
            LocationCode("SYD"),
            LocationCode("ADL"),
            2.0,
            customer,
            1,
        )

        repo.add(assigned)
        repo.add(unassigned)

        self.assertEqual(repo.peek_next_id(), 3)
        self.assertEqual([package.package_id for package in repo.list_all()], [1, 2])
        self.assertEqual([package.package_id for package in repo.list_unassigned()], [1])

    def test_package_repository_lists_pages_and_counts_packages(self) -> None:
        repo = InMemoryPackageRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        assigned_route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=9)
        first = DeliveryPackage(LocationCode("SYD"), LocationCode("MEL"), 1.0, customer, 1)
        second = DeliveryPackage(LocationCode("SYD"), LocationCode("ADL"), 2.0, customer, 2)
        third = DeliveryPackage(LocationCode("MEL"), LocationCode("ADL"), 3.0, customer, 3)
        third.route = assigned_route

        repo.add(third)
        repo.add(first)
        repo.add(second)

        self.assertEqual([package.package_id for package in repo.list_page(limit=2, offset=1)], [2, 3])
        self.assertEqual([package.package_id for package in repo.list_unassigned_page(limit=1, offset=1)], [2])
        page, total = repo.list_page_with_total(limit=2, offset=1)
        unassigned_page, unassigned_total = repo.list_unassigned_page_with_total(limit=1, offset=1)
        self.assertEqual([package.package_id for package in page], [2, 3])
        self.assertEqual(total, 3)
        self.assertEqual([package.package_id for package in unassigned_page], [2])
        self.assertEqual(unassigned_total, 2)
        self.assertEqual(repo.count_all(), 3)
        self.assertEqual(repo.count_unassigned(), 2)

    def test_package_repository_replaces_packages_and_counter(self) -> None:
        repo = InMemoryPackageRepository()
        customer = Customer(customer_id=1, contact=ContactInfo(name="Alice"))
        package = DeliveryPackage(
            LocationCode("SYD"),
            LocationCode("MEL"),
            1.0,
            customer,
            4,
        )

        repo.replace_packages({4: package}, next_id=8)

        self.assertEqual(repo.peek_next_id(), 8)
        self.assertIs(repo.get_by_id(4), package)

    def test_route_repository_rejects_duplicate_id(self) -> None:
        repo = InMemoryRouteRepository()
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=1)
        repo.add(route)

        with self.assertRaises(ValueError) as ctx:
            repo.add(DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=1))

        self.assertIn("Route with ID 1 already exists", str(ctx.exception))

    def test_route_repository_tracks_counter_and_lists_routes_in_id_order(self) -> None:
        repo = InMemoryRouteRepository()
        route_b = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=2)
        route_a = DeliveryRoute(LocationCode("SYD"), LocationCode("ADL"), route_id=1)

        repo.add(route_b)
        repo.add(route_a)

        self.assertEqual(repo.peek_next_id(), 3)
        self.assertEqual([route.route_id for route in repo.list_all()], [1, 2])
        self.assertEqual([route.route_id for route in repo.list_page(limit=1, offset=1)], [2])
        page, total = repo.list_page_with_total(limit=1, offset=1)
        self.assertEqual([route.route_id for route in page], [2])
        self.assertEqual(total, 2)
        self.assertEqual(repo.count_all(), 2)

    def test_route_repository_replaces_routes_and_counter(self) -> None:
        repo = InMemoryRouteRepository()
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("MEL"), route_id=5)

        repo.replace_routes({5: route}, next_id=9)

        self.assertEqual(repo.peek_next_id(), 9)
        self.assertIs(repo.get_by_id(5), route)
