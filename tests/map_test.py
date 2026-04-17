import unittest

from src.domain.services.map import Map


class TestMap_Should(unittest.TestCase):
    def test_get_locations(self):
        expected_locations = ["SYD", "MEL", "ADL", "ASP", "BRI", "DAR", "PER"]
        result = Map.get_locations()

        self.assertEqual(result, expected_locations)
        self.assertIsInstance(result, list)
        self.assertIsNot(result, Map._locations)  # type: ignore[reportPrivateUsage]

    def test_is_valid_location_with_valid_codes(self):
        valid_codes = ["SYD", "MEL", "ADL", "ASP", "BRI", "DAR", "PER"]

        for code in valid_codes:
            with self.subTest(code=code):
                self.assertTrue(Map.is_valid_location(code))

    def test_is_valid_location_with_invalid_codes(self):
        invalid_codes = ["", "INVALID", "syd", "Mel", "SYDNEY", None, 123]

        for code in invalid_codes:
            with self.subTest(code=code):
                self.assertFalse(Map.is_valid_location(code))  # type: ignore[reportArgumentType]

    def test_get_distance_same_location(self):
        locations = Map.get_locations()

        for location in locations:
            with self.subTest(location=location):
                distance = Map.get_distance(location, location)
                self.assertEqual(distance, 0)

    def test_get_distance_valid_pairs(self):
        test_cases = [
            ("SYD", "MEL", 877),
            ("MEL", "SYD", 877),
            ("ADL", "PER", 2785),
            ("PER", "ADL", 2785),
            ("ASP", "DAR", 1497),
            ("DAR", "ASP", 1497),
        ]

        for loc1, loc2, expected_distance in test_cases:
            with self.subTest(loc1=loc1, loc2=loc2):
                distance = Map.get_distance(loc1, loc2)
                self.assertEqual(distance, expected_distance)

    def test_get_distance_invalid_first_location(self):
        with self.assertRaises(ValueError) as context:
            Map.get_distance("INVALID", "SYD")

        self.assertIn("No distance between INVALID and SYD", str(context.exception))

    def test_get_distance_invalid_second_location(self):
        with self.assertRaises(ValueError) as context:
            Map.get_distance("SYD", "INVALID")

        self.assertIn("No distance between SYD and INVALID", str(context.exception))

    def test_get_distance_both_invalid_locations(self):
        with self.assertRaises(ValueError) as context:
            Map.get_distance("INVALID1", "INVALID2")

        self.assertIn("No distance between INVALID1 and INVALID2", str(context.exception))

    def test_distances_symmetry(self):
        locations = Map.get_locations()

        for i, loc1 in enumerate(locations):
            for loc2 in locations[i + 1 :]:  # Avoid testing same pairs twice
                with self.subTest(loc1=loc1, loc2=loc2):
                    distance_ab = Map.get_distance(loc1, loc2)
                    distance_ba = Map.get_distance(loc2, loc1)
                    self.assertEqual(
                        distance_ab,
                        distance_ba,
                        f"Distance {loc1}->{loc2} ({distance_ab}) != {loc2}->{loc1} ({distance_ba})",
                    )

    def test_all_location_pairs_have_distances(self):
        locations = Map.get_locations()

        for loc1 in locations:
            for loc2 in locations:
                with self.subTest(loc1=loc1, loc2=loc2):
                    distance = Map.get_distance(loc1, loc2)
                    self.assertIsInstance(distance, int)
                    self.assertGreaterEqual(distance, 0)
