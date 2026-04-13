import unittest

from src.models.contact_info import ContactInfo
from src.models.customer import Customer


class _FakePackage:
    """Minimal stand-in for DeliveryPackage used by Customer."""

    def __init__(self, package_id: int, customer: Customer | None = None) -> None:
        self.package_id = package_id
        self.customer: Customer | None = customer


class Customer_Should(unittest.TestCase):
    def make_contact(
        self, name: str = "Alice", email: str = "a@x.com", phone: str = "0412345678"
    ) -> ContactInfo:
        return ContactInfo(name=name, email=email, phone_number=phone)

    def test_auto_id_assigned_and_increments(self) -> None:
        # Use the class counter to assert relative sequencing without assuming a global start.
        start = Customer._next_id  # type: ignore[reportPrivateUsage]
        c1 = Customer(self.make_contact("Person1"))
        c2 = Customer(self.make_contact("Person2"))
        self.assertEqual(c1.customer_id, start)
        self.assertEqual(c2.customer_id, start + 1)

    def test_property_proxies(self) -> None:
        ci = self.make_contact("Bob", "bob@ex.com", "0411222333")
        c = Customer(ci)
        self.assertEqual(c.name, "Bob")
        self.assertEqual(c.email, "bob@ex.com")
        self.assertEqual(c.phone_number, "0411222333")

    def test_delivery_packages_is_tuple_and_readonly_view(self) -> None:
        c = Customer(self.make_contact("Carlos"))
        self.assertIsInstance(c.delivery_packages, tuple)
        self.assertEqual(len(c.delivery_packages), 0)
        # Ensure it's a new tuple each time and not directly mutable storage
        p = _FakePackage(1)
        c.add_package(p)  # type: ignore[reportArgumentType]
        t1 = c.delivery_packages
        t2 = c.delivery_packages
        self.assertIsNot(t1, t2)
        self.assertEqual(len(t2), 1)

    def test_add_package_links_both_ways_and_prevents_duplicates(self) -> None:
        c = Customer(self.make_contact("Dean"))
        p = _FakePackage(5)
        c.add_package(p)  # type: ignore[reportArgumentType]
        # Linked
        self.assertIs(p.customer, c)
        self.assertIn(p, c.delivery_packages)
        # Duplicate add -> error
        with self.assertRaises(ValueError):
            c.add_package(p)  # type: ignore[reportArgumentType]

    def test_add_package_reassigns_from_other_customer(self) -> None:
        old = Customer(self.make_contact("Old"))
        new = Customer(self.make_contact("New"))
        p = _FakePackage(9)
        old.add_package(p)  # type: ignore[reportArgumentType]
        self.assertIn(p, old.delivery_packages)
        # Now add to new -> should be moved
        new.add_package(p)  # type: ignore[reportArgumentType]
        self.assertIs(p.customer, new)
        self.assertIn(p, new.delivery_packages)
        self.assertNotIn(p, old.delivery_packages)

    def test_remove_package_happy_clears_package_customer(self) -> None:
        c = Customer(self.make_contact("Eve"))
        p = _FakePackage(7)
        c.add_package(p)  # type: ignore[reportArgumentType]
        c.remove_package(p)  # type: ignore[reportArgumentType]
        self.assertNotIn(p, c.delivery_packages)
        self.assertIsNone(p.customer)

    def test_remove_package_missing_raises(self) -> None:
        c = Customer(self.make_contact("Frank"))
        p = _FakePackage(11)
        with self.assertRaises(ValueError):
            c.remove_package(p)  # type: ignore[reportArgumentType]
