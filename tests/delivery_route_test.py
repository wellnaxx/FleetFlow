import unittest
from src.models.delivery_route import DeliveryRoute

class TestDeliveryRout_Should(unittest.TestCase):
    def test_route_init(self):
        rout = DeliveryRoute("SYD", "MEL", "BRI")

        self.assertEqual(rout.start_location, "SYD")
        self.assertEqual(rout.end_location, "BRI")
        self.assertEqual(rout._locations, ["SYD", "MEL", "BRI"])

    def test_route_single_loc(self):
        with self.assertRaises(ValueError):
            DeliveryRoute("MEL")

    def test_route_empty_loc(self):
        with self.assertRaises(ValueError):
            DeliveryRoute("")

    def test_route_empty_start_loc(self):
        with self.assertRaises(ValueError):
            DeliveryRoute("", "BRI")

    def test_route_empty_end_loc(self):
        with self.assertRaises(ValueError):
            DeliveryRoute("SYD", "")

    def test_route_none_loc(self):
        with self.assertRaises(ValueError):
            DeliveryRoute(None)

    def test_route_none_start_loc(self):
        with self.assertRaises(ValueError):
            DeliveryRoute(None, "BRI")

    def test_route_none_end_loc(self):
        with self.assertRaises(ValueError):
            DeliveryRoute("SYD", None)

    def test_route_wrong_loc(self):
        with self.assertRaises(ValueError):
            DeliveryRoute("SOF", "PLO")


