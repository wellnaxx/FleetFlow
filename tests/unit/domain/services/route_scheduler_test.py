import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

from src.domain.exceptions import DomainValidationError, EntityNotFoundError
from src.domain.services.route_scheduler import RouteScheduler
from src.domain.value_objects.location_code import LocationCode

DEPARTURE = datetime(2025, 1, 1, 8, 0)
AAA = LocationCode("AAA")
BBB = LocationCode("BBB")
CCC = LocationCode("CCC")


class RouteScheduler_Should(unittest.TestCase):
    @patch("src.domain.services.route_scheduler.Map.get_distance", side_effect=[50, 150])
    def test_builds_ordered_segments_and_accumulated_stop_times(
        self,
        get_distance_mock: MagicMock,
    ) -> None:
        schedule = RouteScheduler.build(
            locations=(AAA, BBB, CCC),
            departure_time=DEPARTURE,
            speed_kmph=100,
        )

        self.assertEqual(schedule.departure_time, DEPARTURE)
        self.assertEqual(schedule.total_distance_km, 200)
        self.assertEqual(schedule.arrival_time_at(AAA), DEPARTURE)
        self.assertEqual(schedule.arrival_time_at(BBB), DEPARTURE + timedelta(minutes=30))
        self.assertEqual(schedule.arrival_time_at(CCC), DEPARTURE + timedelta(hours=2))
        self.assertEqual(schedule.eta_final, DEPARTURE + timedelta(hours=2))
        self.assertEqual(
            get_distance_mock.call_args_list,
            [call(AAA, BBB), call(BBB, CCC)],
        )

    @patch("src.domain.services.route_scheduler.Map.get_distance", return_value=87)
    def test_uses_default_speed_when_speed_is_omitted(self, _: object) -> None:
        schedule = RouteScheduler.build(
            locations=(AAA, BBB),
            departure_time=DEPARTURE,
        )

        self.assertEqual(schedule.segments[0].duration, timedelta(hours=1))
        self.assertEqual(schedule.eta_final, DEPARTURE + timedelta(hours=1))

    @patch("src.domain.services.route_scheduler.Map.get_distance")
    def test_rejects_fewer_than_two_locations_without_reading_map(
        self,
        get_distance_mock: MagicMock,
    ) -> None:
        with self.assertRaisesRegex(DomainValidationError, "at least two"):
            RouteScheduler.build(
                locations=(AAA,),
                departure_time=DEPARTURE,
            )

        get_distance_mock.assert_not_called()

    @patch("src.domain.services.route_scheduler.Map.get_distance")
    def test_rejects_non_positive_speed_without_reading_map(
        self,
        get_distance_mock: MagicMock,
    ) -> None:
        for speed in (0, -1):
            with self.subTest(speed=speed), self.assertRaisesRegex(DomainValidationError, "positive"):
                RouteScheduler.build(
                    locations=(AAA, BBB),
                    departure_time=DEPARTURE,
                    speed_kmph=speed,
                )

        get_distance_mock.assert_not_called()

    @patch(
        "src.domain.services.route_scheduler.Map.get_distance",
        side_effect=EntityNotFoundError("No distance between AAA and BBB"),
    )
    def test_propagates_missing_map_distance(self, _: object) -> None:
        with self.assertRaisesRegex(EntityNotFoundError, "No distance"):
            RouteScheduler.build(
                locations=(AAA, BBB),
                departure_time=DEPARTURE,
            )

    @patch("src.domain.services.route_scheduler.Map.get_distance", return_value=100)
    def test_returns_tuple_backed_schedule_collections(self, _: object) -> None:
        schedule = RouteScheduler.build(
            locations=(AAA, BBB),
            departure_time=DEPARTURE,
            speed_kmph=100,
        )

        self.assertIsInstance(schedule.segments, tuple)
        self.assertIsInstance(schedule.stops, tuple)
