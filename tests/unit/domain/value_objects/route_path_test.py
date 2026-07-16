import unittest
from unittest.mock import patch

from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.route_path import RoutePath

SUPPORTED_LOCATIONS = (
    LocationCode("AAA"),
    LocationCode("BBB"),
    LocationCode("CCC"),
    LocationCode("DDD"),
)


@patch("src.domain.value_objects.route_path.Map.get_locations", return_value=SUPPORTED_LOCATIONS)
class RoutePathShould(unittest.TestCase):
    def test_create_normalizes_locations_and_exposes_endpoints(self, *_: object) -> None:
        path = RoutePath.create(" aaa ", LocationCode("bbb"), "CCC")

        self.assertEqual(
            path.locations,
            (LocationCode("AAA"), LocationCode("BBB"), LocationCode("CCC")),
        )
        self.assertEqual(path.start, LocationCode("AAA"))
        self.assertEqual(path.end, LocationCode("CCC"))

    def test_direct_construction_accepts_canonical_locations(self, *_: object) -> None:
        path = RoutePath((LocationCode("AAA"), LocationCode("BBB")))

        self.assertEqual(path.locations, (LocationCode("AAA"), LocationCode("BBB")))

    def test_direct_construction_rejects_noncanonical_locations(self, *_: object) -> None:
        invalid_collections: tuple[object, ...] = (
            ("AAA", "BBB"),
            [LocationCode("AAA"), LocationCode("BBB")],
        )

        for locations in invalid_collections:
            with self.subTest(locations=locations), self.assertRaisesRegex(
                DomainValidationError,
                "tuple of LocationCode instances",
            ):
                RoutePath(locations)  # type: ignore[reportArgumentType]

    def test_rejects_fewer_than_two_locations(self, *_: object) -> None:
        for locations in ((), ("AAA",)):
            with self.subTest(locations=locations), self.assertRaisesRegex(
                DomainValidationError,
                "at least two",
            ):
                RoutePath.create(*locations)

    def test_rejects_unsupported_location(self, *_: object) -> None:
        with self.assertRaisesRegex(DomainValidationError, "Invalid location code: ZZZ"):
            RoutePath.create("AAA", "ZZZ")

    def test_rejects_duplicates_after_normalization(self, *_: object) -> None:
        with self.assertRaisesRegex(DomainValidationError, "duplicate"):
            RoutePath.create("AAA", "BBB", " aaa ")

    def test_includes_locations_only_in_forward_order(self, *_: object) -> None:
        path = RoutePath.create("AAA", "BBB", "CCC", "DDD")

        self.assertTrue(path.includes_in_order("AAA", LocationCode("DDD")))
        self.assertTrue(path.includes_in_order("BBB", "CCC"))
        self.assertFalse(path.includes_in_order("CCC", "BBB"))
        self.assertFalse(path.includes_in_order("AAA", "AAA"))
        self.assertFalse(path.includes_in_order("AAA", "ZZZ"))

    def test_is_immutable(self, *_: object) -> None:
        path = RoutePath.create("AAA", "BBB")

        with self.assertRaises((AttributeError, TypeError)):
            path.locations = (LocationCode("BBB"), LocationCode("AAA"))  # type: ignore[misc]
