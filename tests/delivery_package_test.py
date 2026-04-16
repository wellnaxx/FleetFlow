import unittest

from domain.entities.customer import Customer
from domain.entities.delivery_package import DeliveryPackage
from domain.value_objects.contact_info import ContactInfo


class TestDeliveryPackage_Should(unittest.TestCase):
    def test_package_init_and_id_increments(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))

        p1 = DeliveryPackage("SYD", "BRI", 500, customer)
        p2 = DeliveryPackage("MEL", "ADL", 250, customer)

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
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))
        with self.assertRaises(ValueError):
            DeliveryPackage("SOF", "BRI", 500, customer)

    def test_package_wrong_end_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))
        with self.assertRaises(ValueError):
            DeliveryPackage("SYD", "SOF", 500, customer)

    def test_package_empty_start_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))
        with self.assertRaises(ValueError):
            DeliveryPackage("", "SOF", 500, customer)

    def test_package_empty_end_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))
        with self.assertRaises(ValueError):
            DeliveryPackage("SYD", "", 500, customer)

    def test_package_same_start_end_loc(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))
        with self.assertRaises(ValueError):
            DeliveryPackage("SYD", "SYD", 500, customer)

    def test_package_negative_weight(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))
        with self.assertRaises(ValueError):
            DeliveryPackage("SYD", "BRI", -500, customer)

    def test_package_zero_weight(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))
        with self.assertRaises(ValueError):
            DeliveryPackage("SYD", "BRI", 0, customer)

    def test_package_customer_empty_name(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("", "dan@e.com", "0484568777"))

    def test_package_customer_int_name(self):
        with self.assertRaises(TypeError):
            Customer(ContactInfo(150, "dan@e.com", "0484568777"))  # type: ignore[reportArgumentType]

    def test_package_customer_short_name(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Da", "dan@e.com", "0484568777"))

    def test_package_customer_long_name(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Da" * 16, "dan@e.com", "0484568777"))

    def test_package_customer_at_email(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Dan", "dane.com", "0484568777"))

    def test_package_customer_dot_email(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Dan", "dan@ecom", "0484568777"))

    def test_package_customer_int_phone(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Dan", "dan@ecom", 484568777))  # type: ignore[reportArgumentType]

    def test_package_customer_len_phone(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Dan", "dan@ecom", "042588997"))

    def test_package_customer_start_num_phone(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Dan", "dan@ecom", "082588997"))
