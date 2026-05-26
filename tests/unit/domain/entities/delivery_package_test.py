import unittest
from datetime import datetime

from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode


class TestDeliveryPackage_Should(unittest.TestCase):
    def test_package_init_and_id_increments(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)

        p1 = DeliveryPackage(LocationCode("SYD"), LocationCode("BRI"), 500, customer, 1)
        p2 = DeliveryPackage(LocationCode("MEL"), LocationCode("ADL"), 250, customer, 2)

        # Field checks for the first package
        self.assertEqual(p1.start_location, "SYD")
        self.assertEqual(p1.end_location, "BRI")
        self.assertEqual(p1.weight, 500)
        assert p1.customer is not None
        self.assertEqual(p1.customer.name, "Dan")
        self.assertEqual(p1.customer.email, "dan@e.com")
        self.assertEqual(p1.customer.phone_number, "0484568777")

        # ID behavior: integers and sequential within this test
        self.assertIsInstance(p1.package_id, int)
        self.assertIsInstance(p2.package_id, int)
        self.assertEqual(p2.package_id, p1.package_id + 1)

    def test_package_wrong_start_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        with self.assertRaises(DomainValidationError):
            DeliveryPackage(LocationCode("SOF"), LocationCode("BRI"), 500, customer, 1)

    def test_package_wrong_end_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        with self.assertRaises(DomainValidationError):
            DeliveryPackage(LocationCode("SYD"), LocationCode("SOF"), 500, customer, 1)

    def test_package_empty_start_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        with self.assertRaises(DomainValidationError):
            DeliveryPackage(LocationCode(""), LocationCode("SOF"), 500, customer, 1)

    def test_package_empty_end_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        with self.assertRaises(DomainValidationError):
            DeliveryPackage(LocationCode("SYD"), LocationCode(""), 500, customer, 1)

    def test_package_same_start_end_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        with self.assertRaises(DomainValidationError):
            DeliveryPackage(LocationCode("SYD"), LocationCode("SYD"), 500, customer, 1)

    def test_package_negative_weight(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        with self.assertRaises(DomainValidationError):
            DeliveryPackage(LocationCode("SYD"), LocationCode("BRI"), -500, customer, 1)

    def test_package_zero_weight(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        with self.assertRaises(DomainValidationError):
            DeliveryPackage(LocationCode("SYD"), LocationCode("BRI"), 0, customer, 1)

    def test_package_customer_empty_name(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo(LocationCode(""), "dan@e.com", "0484568777"), 1)

    def test_package_customer_int_name(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo(150, "dan@e.com", "0484568777"), 1)  # type: ignore[reportArgumentType]

    def test_package_customer_short_name(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo("Da", "dan@e.com", "0484568777"), 1)

    def test_package_customer_long_name(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo("Da" * 16, "dan@e.com", "0484568777"), 1)

    def test_package_customer_at_email(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo("Dan", "dane.com", "0484568777"), 1)

    def test_package_customer_dot_email(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo("Dan", "dan@ecom", "0484568777"), 1)

    def test_package_customer_int_phone(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo("Dan", "dan@ecom", 484568777), 1)  # type: ignore[reportArgumentType]

    def test_package_customer_len_phone(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo("Dan", "dan@ecom", "042588997"), 1)

    def test_package_customer_start_num_phone(self):
        with self.assertRaises(DomainValidationError):
            Customer(ContactInfo("Dan", "dan@ecom", "082588997"), 1)

    def test_snapshot_state_restores_mutable_assignment_state(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), 1)
        package = DeliveryPackage(LocationCode("SYD"), LocationCode("BRI"), 500, customer, 1)
        route = object()
        expected_arrival = datetime(2025, 1, 1, 12, 0)
        package.route = route  # type: ignore[assignment]
        package.status = ItemStatus.IN_PROGRESS
        package.current_location = LocationCode("MEL")
        package.expected_arrival = expected_arrival
        snapshot = package.snapshot_state()

        package.reset_assignment_state()

        package.restore_state(snapshot)

        self.assertIs(package.route, route)
        self.assertEqual(package.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(package.current_location, LocationCode("MEL"))
        self.assertEqual(package.expected_arrival, expected_arrival)
