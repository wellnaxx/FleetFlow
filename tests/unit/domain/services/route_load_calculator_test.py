import unittest

from src.domain.services.route_load_calculator import RouteLoadCalculator
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.package_load import PackageLoad

AAA = LocationCode("AAA")
BBB = LocationCode("BBB")
CCC = LocationCode("CCC")
DDD = LocationCode("DDD")


class RouteLoadCalculatorShould(unittest.TestCase):
    def test_use_simultaneous_not_total_package_weight(self) -> None:
        packages = (
            PackageLoad(AAA, BBB, 40),
            PackageLoad(BBB, CCC, 40),
        )

        result = RouteLoadCalculator.maximum_segment_load(
            locations=(AAA, BBB, CCC, DDD),
            packages=packages,
        )

        self.assertEqual(result, 40)

    def test_include_optional_candidate(self) -> None:
        assigned = PackageLoad(AAA, CCC, 30)
        candidate = PackageLoad(BBB, DDD, 30)

        result = RouteLoadCalculator.maximum_segment_load(
            locations=(AAA, BBB, CCC, DDD),
            packages=(assigned,),
            extra_package=candidate,
        )

        self.assertEqual(result, 60)

    def test_ignore_packages_outside_or_reversed_on_route(self) -> None:
        packages = (
            PackageLoad(AAA, LocationCode("ZZZ"), 30),
            PackageLoad(CCC, BBB, 30),
        )

        result = RouteLoadCalculator.maximum_segment_load(
            locations=(AAA, BBB, CCC),
            packages=packages,
        )

        self.assertEqual(result, 0.0)

    def test_return_zero_without_route_segments(self) -> None:
        result = RouteLoadCalculator.maximum_segment_load(
            locations=(),
            packages=(),
        )

        self.assertEqual(result, 0.0)
