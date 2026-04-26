import unittest

from src.domain.value_objects.location_code import LocationCode, location_code_or_none


class LocationCode_Should(unittest.TestCase):
    def test_wraps_string_values(self) -> None:
        code = LocationCode("SYD")

        self.assertIsInstance(code, str)
        self.assertEqual(code, "SYD")

    def test_rejects_non_string_values(self) -> None:
        with self.assertRaises(TypeError):
            LocationCode(123)  # type: ignore[reportArgumentType]

    def test_rejects_blank_values(self) -> None:
        with self.assertRaises(ValueError):
            LocationCode("")
            LocationCode("     ")

    def test_location_code_normalizes_whitespace_and_case(self) -> None:
        code = LocationCode(" syd ")

        self.assertEqual(code, "SYD")
        self.assertIsInstance(code, LocationCode)

    def test_optional_converter_preserves_none(self) -> None:
        self.assertIsNone(location_code_or_none(None))


    

