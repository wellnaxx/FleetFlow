import unittest

from src.domain.exceptions import EntityNotFoundError
from src.domain.services.map import Map
from src.domain.value_objects.location_code import LocationCode


class TestMap_Should(unittest.TestCase):
    def test_get_locations_returns_supported_location_codes_in_order(self) -> None:
        expected_locations = [
            LocationCode("SYD"),
            LocationCode("MEL"),
            LocationCode("ADL"),
            LocationCode("ASP"),
            LocationCode("BRI"),
            LocationCode("DAR"),
            LocationCode("PER"),
        ]

        result = Map.get_locations()

        self.assertEqual(result, expected_locations)
        self.assertIsInstance(result, list)
        self.assertIsNot(result, Map._locations)  # type: ignore[reportPrivateUsage]

    def test_get_locations_returns_copy_of_supported_locations(self) -> None:
        locations = Map.get_locations()
        locations.clear()

        self.assertEqual(
            Map.get_locations(),
            [
                LocationCode("SYD"),
                LocationCode("MEL"),
                LocationCode("ADL"),
                LocationCode("ASP"),
                LocationCode("BRI"),
                LocationCode("DAR"),
                LocationCode("PER"),
            ],
        )

    def test_is_valid_location_accepts_supported_location_codes(self) -> None:
        valid_codes = [
            LocationCode("SYD"),
            LocationCode("MEL"),
            LocationCode("ADL"),
            LocationCode("ASP"),
            LocationCode("BRI"),
            LocationCode("DAR"),
            LocationCode("PER"),
        ]

        for code in valid_codes:
            with self.subTest(code=code):
                self.assertTrue(Map.is_valid_location(code))

    def test_is_valid_location_accepts_and_normalizes_raw_strings(self) -> None:
        valid_raw_codes = ["SYD", "syd", " syd ", "Mel", " per "]

        for code in valid_raw_codes:
            with self.subTest(code=code):
                self.assertTrue(Map.is_valid_location(code))

    def test_is_valid_location_rejects_unknown_or_invalid_values(self) -> None:
        invalid_codes: list[object] = ["", "   ", "INVALID", "SYDNEY", None, 123]

        for code in invalid_codes:
            with self.subTest(code=code):
                self.assertFalse(Map.is_valid_location(code))

    def test_get_distance_returns_zero_for_same_location(self) -> None:
        for location in Map.get_locations():
            with self.subTest(location=location):
                self.assertEqual(Map.get_distance(location, location), 0)

    def test_get_distance_accepts_raw_strings(self) -> None:
        self.assertEqual(Map.get_distance("SYD", "MEL"), 877)

    def test_get_distance_accepts_typed_location_codes(self) -> None:
        self.assertEqual(
            Map.get_distance(LocationCode("SYD"), LocationCode("MEL")),
            877,
        )

    def test_get_distance_normalizes_raw_strings(self) -> None:
        self.assertEqual(Map.get_distance(" syd ", "mel"), 877)

    def test_get_distance_valid_pairs(self) -> None:
        test_cases = [
            (LocationCode("SYD"), LocationCode("MEL"), 877),
            (LocationCode("MEL"), LocationCode("SYD"), 877),
            (LocationCode("ADL"), LocationCode("PER"), 2785),
            (LocationCode("PER"), LocationCode("ADL"), 2785),
            (LocationCode("ASP"), LocationCode("DAR"), 1497),
            (LocationCode("DAR"), LocationCode("ASP"), 1497),
        ]

        for loc1, loc2, expected_distance in test_cases:
            with self.subTest(loc1=loc1, loc2=loc2):
                self.assertEqual(Map.get_distance(loc1, loc2), expected_distance)

    def test_get_distance_rejects_invalid_first_location(self) -> None:
        with self.assertRaises(EntityNotFoundError) as context:
            Map.get_distance("INVALID", "SYD")

        self.assertIn("No distance between INVALID and SYD", str(context.exception))

    def test_get_distance_rejects_invalid_second_location(self) -> None:
        with self.assertRaises(EntityNotFoundError) as context:
            Map.get_distance("SYD", "INVALID")

        self.assertIn("No distance between SYD and INVALID", str(context.exception))

    def test_get_distance_rejects_two_invalid_locations(self) -> None:
        with self.assertRaises(EntityNotFoundError) as context:
            Map.get_distance("INVALID1", "INVALID2")

        self.assertIn("No distance between INVALID1 and INVALID2", str(context.exception))

    def test_distances_are_symmetric_for_all_supported_location_pairs(self) -> None:
        locations = Map.get_locations()

        for index, loc1 in enumerate(locations):
            for loc2 in locations[index + 1 :]:
                with self.subTest(loc1=loc1, loc2=loc2):
                    distance_ab = Map.get_distance(loc1, loc2)
                    distance_ba = Map.get_distance(loc2, loc1)

                    self.assertEqual(
                        distance_ab,
                        distance_ba,
                        f"Distance {loc1}->{loc2} ({distance_ab}) != {loc2}->{loc1} ({distance_ba})",
                    )

    def test_all_supported_location_pairs_have_non_negative_integer_distances(self) -> None:
        locations = Map.get_locations()

        for loc1 in locations:
            for loc2 in locations:
                with self.subTest(loc1=loc1, loc2=loc2):
                    distance = Map.get_distance(loc1, loc2)

                    self.assertIsInstance(distance, int)
                    self.assertGreaterEqual(distance, 0)
