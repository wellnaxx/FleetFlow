import unittest
from datetime import UTC, datetime, timedelta

from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.route_schedule import (
    RoutePosition,
    RoutePositionKind,
    RouteSchedule,
    RouteSegment,
    ScheduledStop,
)

DEPARTURE = datetime(2025, 1, 1, 8, 0)
AAA = LocationCode("AAA")
BBB = LocationCode("BBB")
CCC = LocationCode("CCC")
ONE_HOUR = timedelta(hours=1)


def make_schedule() -> RouteSchedule:
    return RouteSchedule(
        departure_time=DEPARTURE,
        segments=(
            RouteSegment(start=AAA, end=BBB, distance_km=100, duration=ONE_HOUR),
            RouteSegment(start=BBB, end=CCC, distance_km=150, duration=ONE_HOUR),
        ),
        stops=(
            ScheduledStop(location=AAA, arrival_at=DEPARTURE),
            ScheduledStop(location=BBB, arrival_at=DEPARTURE + ONE_HOUR),
            ScheduledStop(location=CCC, arrival_at=DEPARTURE + 2 * ONE_HOUR),
        ),
    )


class RouteSchedule_Should(unittest.TestCase):
    def test_exposes_final_eta_total_distance_and_arrival_lookups(self) -> None:
        schedule = make_schedule()

        self.assertEqual(schedule.eta_final, DEPARTURE + 2 * ONE_HOUR)
        self.assertEqual(schedule.total_distance_km, 250)
        self.assertEqual(schedule.arrival_time_at(AAA), DEPARTURE)
        self.assertEqual(schedule.arrival_time_at(BBB), DEPARTURE + ONE_HOUR)
        self.assertEqual(schedule.arrival_time_at(CCC), DEPARTURE + 2 * ONE_HOUR)

    def test_rejects_arrival_lookup_for_location_outside_schedule(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "not part of this schedule"):
            make_schedule().arrival_time_at(LocationCode("DDD"))

    def test_reports_position_at_every_schedule_boundary(self) -> None:
        schedule = make_schedule()
        test_cases = [
            (
                "before departure",
                DEPARTURE - timedelta(seconds=1),
                RoutePosition(
                    kind=RoutePositionKind.BEFORE_START,
                    stop_city=AAA,
                    next_eta=DEPARTURE,
                ),
            ),
            (
                "at departure",
                DEPARTURE,
                RoutePosition(
                    kind=RoutePositionKind.IN_TRANSIT,
                    from_city=AAA,
                    to_city=BBB,
                    next_eta=DEPARTURE + ONE_HOUR,
                ),
            ),
            (
                "during first segment",
                DEPARTURE + timedelta(minutes=30),
                RoutePosition(
                    kind=RoutePositionKind.IN_TRANSIT,
                    from_city=AAA,
                    to_city=BBB,
                    next_eta=DEPARTURE + ONE_HOUR,
                ),
            ),
            (
                "at intermediate stop",
                DEPARTURE + ONE_HOUR,
                RoutePosition(
                    kind=RoutePositionKind.AT_STOP,
                    stop_city=BBB,
                    next_eta=DEPARTURE + 2 * ONE_HOUR,
                ),
            ),
            (
                "during final segment",
                DEPARTURE + timedelta(hours=1, minutes=30),
                RoutePosition(
                    kind=RoutePositionKind.IN_TRANSIT,
                    from_city=BBB,
                    to_city=CCC,
                    next_eta=DEPARTURE + 2 * ONE_HOUR,
                ),
            ),
            (
                "at final stop",
                DEPARTURE + 2 * ONE_HOUR,
                RoutePosition(
                    kind=RoutePositionKind.AT_STOP,
                    stop_city=CCC,
                ),
            ),
            (
                "after final stop",
                DEPARTURE + 2 * ONE_HOUR + timedelta(seconds=1),
                RoutePosition(
                    kind=RoutePositionKind.AFTER_END,
                    stop_city=CCC,
                ),
            ),
        ]

        for label, now, expected in test_cases:
            with self.subTest(label=label):
                self.assertEqual(schedule.position_at(now), expected)

    def test_rejects_fewer_than_two_stops(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "at least two stops"):
            RouteSchedule(
                departure_time=DEPARTURE,
                segments=(),
                stops=(ScheduledStop(location=AAA, arrival_at=DEPARTURE),),
            )

    def test_rejects_segment_count_that_does_not_connect_every_stop(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "one segment between each pair"):
            RouteSchedule(
                departure_time=DEPARTURE,
                segments=(RouteSegment(start=AAA, end=BBB, distance_km=100, duration=ONE_HOUR),),
                stops=(
                    ScheduledStop(location=AAA, arrival_at=DEPARTURE),
                    ScheduledStop(location=BBB, arrival_at=DEPARTURE + ONE_HOUR),
                    ScheduledStop(location=CCC, arrival_at=DEPARTURE + 2 * ONE_HOUR),
                ),
            )

    def test_rejects_first_stop_that_does_not_match_departure_time(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "first stop arrival"):
            RouteSchedule(
                departure_time=DEPARTURE,
                segments=(RouteSegment(start=AAA, end=BBB, distance_km=100, duration=ONE_HOUR),),
                stops=(
                    ScheduledStop(location=AAA, arrival_at=DEPARTURE + timedelta(minutes=1)),
                    ScheduledStop(location=BBB, arrival_at=DEPARTURE + timedelta(hours=1, minutes=1)),
                ),
            )

    def test_rejects_duplicate_stop_locations(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "duplicate locations"):
            RouteSchedule(
                departure_time=DEPARTURE,
                segments=(RouteSegment(start=AAA, end=AAA, distance_km=100, duration=ONE_HOUR),),
                stops=(
                    ScheduledStop(location=AAA, arrival_at=DEPARTURE),
                    ScheduledStop(location=AAA, arrival_at=DEPARTURE + ONE_HOUR),
                ),
            )

    def test_rejects_non_positive_segment_distance_or_duration(self) -> None:
        invalid_segments = [
            (
                "distance",
                RouteSegment(start=AAA, end=BBB, distance_km=0, duration=ONE_HOUR),
                DEPARTURE + ONE_HOUR,
            ),
            (
                "duration",
                RouteSegment(start=AAA, end=BBB, distance_km=100, duration=timedelta(0)),
                DEPARTURE,
            ),
        ]

        for expected_message, segment, arrival_at in invalid_segments:
            with (
                self.subTest(field=expected_message),
                self.assertRaisesRegex(
                    DomainValidationError,
                    expected_message,
                ),
            ):
                RouteSchedule(
                    departure_time=DEPARTURE,
                    segments=(segment,),
                    stops=(
                        ScheduledStop(location=AAA, arrival_at=DEPARTURE),
                        ScheduledStop(location=BBB, arrival_at=arrival_at),
                    ),
                )

    def test_rejects_segment_locations_that_do_not_match_adjacent_stops(self) -> None:
        invalid_segments = [
            ("start", RouteSegment(start=CCC, end=BBB, distance_km=100, duration=ONE_HOUR)),
            ("end", RouteSegment(start=AAA, end=CCC, distance_km=100, duration=ONE_HOUR)),
        ]

        for expected_message, segment in invalid_segments:
            with (
                self.subTest(field=expected_message),
                self.assertRaisesRegex(
                    DomainValidationError,
                    expected_message,
                ),
            ):
                RouteSchedule(
                    departure_time=DEPARTURE,
                    segments=(segment,),
                    stops=(
                        ScheduledStop(location=AAA, arrival_at=DEPARTURE),
                        ScheduledStop(location=BBB, arrival_at=DEPARTURE + ONE_HOUR),
                    ),
                )

    def test_rejects_stop_time_that_does_not_match_segment_duration(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "duration does not match"):
            RouteSchedule(
                departure_time=DEPARTURE,
                segments=(RouteSegment(start=AAA, end=BBB, distance_km=100, duration=ONE_HOUR),),
                stops=(
                    ScheduledStop(location=AAA, arrival_at=DEPARTURE),
                    ScheduledStop(location=BBB, arrival_at=DEPARTURE + timedelta(hours=2)),
                ),
            )

    def test_rejects_timezone_aware_schedule_timestamps(self) -> None:
        aware_departure = DEPARTURE.replace(tzinfo=UTC)
        with self.assertRaisesRegex(DomainValidationError, "timestamps must be timezone-naive"):
            RouteSchedule(
                departure_time=aware_departure,
                segments=(RouteSegment(start=AAA, end=BBB, distance_km=100, duration=ONE_HOUR),),
                stops=(
                    ScheduledStop(location=AAA, arrival_at=aware_departure),
                    ScheduledStop(location=BBB, arrival_at=aware_departure + ONE_HOUR),
                ),
            )

        with self.assertRaisesRegex(DomainValidationError, "timestamps must be timezone-naive"):
            RouteSchedule(
                departure_time=DEPARTURE,
                segments=(RouteSegment(start=AAA, end=BBB, distance_km=100, duration=ONE_HOUR),),
                stops=(
                    ScheduledStop(location=AAA, arrival_at=DEPARTURE),
                    ScheduledStop(
                        location=BBB,
                        arrival_at=(DEPARTURE + ONE_HOUR).replace(tzinfo=UTC),
                    ),
                ),
            )

    def test_position_at_rejects_timezone_aware_business_time(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "position time must be a timezone-naive"):
            make_schedule().position_at(DEPARTURE.replace(tzinfo=UTC))
