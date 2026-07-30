import unittest
from datetime import datetime

from src.domain.entities.customer import Customer
from src.domain.events.customer_events import CustomerCreated
from src.domain.exceptions import DomainConflictError, DomainValidationError, EntityNotFoundError
from src.domain.value_objects.contact_info import ContactInfo


class _FakePackage:
    """Minimal stand-in for DeliveryPackage used by Customer."""

    def __init__(self, package_id: int, customer: Customer) -> None:
        self.package_id = package_id
        self.customer = customer


class Customer_Should(unittest.TestCase):
    def make_contact(
        self, name: str = "Alice", email: str = "a@x.com", phone: str = "0412345678"
    ) -> ContactInfo:
        return ContactInfo(name=name, email=email, phone_number=phone)

    def test_property_proxies(self) -> None:
        ci = self.make_contact("Bob", "bob@ex.com", "0411222333")
        c = Customer(ci, 1)
        self.assertEqual(c.name, "Bob")
        self.assertEqual(c.email, "bob@ex.com")
        self.assertEqual(c.phone_number, "0411222333")

    def test_create_records_exactly_one_customer_created_event(self) -> None:
        occurred_at = datetime(2026, 6, 13, 10, 30)

        customer = Customer.create(
            contact=self.make_contact(),
            customer_id=17,
            occurred_at=occurred_at,
        )

        self.assertEqual(len(customer.pending_events), 1)
        event = customer.pending_events[0]
        if not isinstance(event, CustomerCreated):
            self.fail(f"Expected CustomerCreated, got {type(event).__name__}.")
        self.assertEqual(event.customer_id, 17)
        self.assertEqual(event.event_version, 1)
        self.assertFalse(hasattr(event, "name"))
        self.assertFalse(hasattr(event, "email"))
        self.assertFalse(hasattr(event, "phone_number"))
        self.assertEqual(event.occurred_at, occurred_at)

    def test_direct_construction_does_not_record_creation_event(self) -> None:
        customer = Customer(contact=self.make_contact(), customer_id=17)

        self.assertEqual(customer.pending_events, ())

    def test_customers_with_matching_data_remain_distinct_entities(self) -> None:
        first = Customer(contact=self.make_contact(), customer_id=17)
        second = Customer(contact=self.make_contact(), customer_id=17)

        self.assertIsNot(first, second)
        self.assertNotEqual(first, second)

    def test_constructor_rejects_invalid_customer_id(self) -> None:
        for customer_id in (0, -1, True, 1.0, "1"):
            with self.subTest(customer_id=customer_id), self.assertRaises(DomainValidationError):
                Customer(
                    contact=self.make_contact(),
                    customer_id=customer_id,  # type: ignore[reportArgumentType]
                )

    def test_delivery_packages_is_tuple_and_readonly_view(self) -> None:
        c = Customer(self.make_contact("Carlos"), 2)
        self.assertIsInstance(c.delivery_packages, tuple)
        self.assertEqual(len(c.delivery_packages), 0)
        # Ensure it's a new tuple each time and not directly mutable storage
        p = _FakePackage(1, c)
        c.add_package(p)  # type: ignore[reportArgumentType]
        t1 = c.delivery_packages
        t2 = c.delivery_packages
        self.assertIsNot(t1, t2)
        self.assertEqual(len(t2), 1)

    def test_add_package_links_both_ways_and_prevents_duplicates(self) -> None:
        c = Customer(self.make_contact("Dean"), 3)
        p = _FakePackage(5, c)
        c.add_package(p)  # type: ignore[reportArgumentType]
        # Linked
        self.assertIs(p.customer, c)
        self.assertIn(p, c.delivery_packages)
        # Duplicate add -> error
        with self.assertRaises(DomainConflictError):
            c.add_package(p)  # type: ignore[reportArgumentType]

    def test_add_package_reassigns_from_other_customer(self) -> None:
        old = Customer(self.make_contact("Old"), 4)
        new = Customer(self.make_contact("New"), 5)
        p = _FakePackage(9, old)
        old.add_package(p)  # type: ignore[reportArgumentType]
        self.assertIn(p, old.delivery_packages)
        # Now add to new -> should be moved
        new.add_package(p)  # type: ignore[reportArgumentType]
        self.assertIs(p.customer, new)
        self.assertIn(p, new.delivery_packages)
        self.assertNotIn(p, old.delivery_packages)

    def test_remove_package_unlinks_existing_package(self) -> None:
        c = Customer(self.make_contact("Frank"), 7)
        p = _FakePackage(11, c)
        c.add_package(p)  # type: ignore[reportArgumentType]

        c.remove_package(p)  # type: ignore[reportArgumentType]

        self.assertNotIn(p, c.delivery_packages)
        self.assertIs(p.customer, c)

    def test_remove_package_missing_raises(self) -> None:
        c = Customer(self.make_contact("Frank"), 7)
        p = _FakePackage(11, c)
        with self.assertRaises(EntityNotFoundError):
            c.remove_package(p)  # type: ignore[reportArgumentType]
