import unittest
from src.models.delivery_package import DeliveryPackage
from src.models.contact_info import ContactInfo
from src.models.customer import Customer

class TestDeliveryPackage_Should(unittest.TestCase):
    def test_package_init(self):
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"))
        package = DeliveryPackage("SYD", "BRI", 500, customer)

        self.assertEqual(package.start_location, "SYD")
        self.assertEqual(package.end_location, "BRI")
        self.assertEqual(package.weight, 500)
        self.assertEqual(package.customer.name, "Dan")
        self.assertEqual(package.customer.email, "dan@e.com")
        self.assertEqual(package.customer.phone_number, "0484568777")
        self.assertEqual(package.package_id, 1)

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
        with self.assertRaises(ValueError):
            Customer(ContactInfo(150, "dan@e.com", "0484568777"))

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
            Customer(ContactInfo("Dan", "dan@ecom", 484568777))

    def test_package_customer_len_phone(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Dan", "dan@ecom", "042588997"))

    def test_package_customer_start_num_phone(self):
        with self.assertRaises(ValueError):
            Customer(ContactInfo("Dan", "dan@ecom", "082588997"))