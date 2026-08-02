"""Tests for PostgreSQL fleet-overview row mapping."""

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.executor import RowDict
from src.adapters.driven.persistence.database.mappers.fleet_overview import (
    map_active_route_overview,
    map_active_route_overviews,
    map_package_overview,
    map_route_overview,
    map_truck_overview,
)
from src.application.results.fleet_overview import AtStopPosition, InTransitPosition
from src.domain.enums.route_status import RouteStatus
from src.domain.services.route_scheduler import RouteScheduler
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.route_schedule import RoutePosition, RoutePositionKind

MODULE = "src.adapters.driven.persistence.database.mappers.fleet_overview"

DEPARTURE = datetime(2030, 1, 1, 8, 0)
SYD = LocationCode("SYD")
MEL = LocationCode("MEL")
ADL = LocationCode("ADL")


def _schedule(
    departure: datetime = DEPARTURE,
    locations: tuple[LocationCode, ...] = (SYD, MEL, ADL),
):
    """Build the schedule used to derive exact temporal test boundaries."""
    return RouteScheduler.build(locations=locations, departure_time=departure)


def _package_count_row(**overrides: object) -> RowDict:
    """Return a valid package aggregate row with selected overrides."""
    row: RowDict = {
        "todo": 3,
        "in_progress": 2,
        "done": 1,
        "unassigned": 2,
        "past_due": 1,
    }
    row.update(overrides)
    return row


def _truck_count_row(**overrides: object) -> RowDict:
    """Return a valid truck aggregate row with selected overrides."""
    row: RowDict = {"free": 2, "on_the_way": 1, "unknown_location": 1}
    row.update(overrides)
    return row


def _candidate(
    *,
    route_id: int,
    departure: datetime,
    stops: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Return a JSON-shaped past-due route candidate."""
    return {
        "route_id": route_id,
        "departure_time": departure.isoformat(),
        "stops": stops
        if stops is not None
        else [
            {"stop_order": 0, "location_code": "SYD"},
            {"stop_order": 1, "location_code": "MEL"},
        ],
    }


def _route_count_row(
    *,
    candidates: object | None = None,
    **overrides: object,
) -> RowDict:
    """Return a valid route aggregate row with selected overrides."""
    row: RowDict = {
        "planned": 1,
        "scheduled": 2,
        "in_progress": 1,
        "completed": 1,
        "past_due_candidates": [] if candidates is None else candidates,
    }
    row.update(overrides)
    return row


def _active_route_rows(
    *,
    route_id: int = 21,
    departure: datetime = DEPARTURE,
    status: str = RouteStatus.IN_PROGRESS.value,
    truck_vehicle_id: int | None = 1001,
    truck_capacity: int | None = 1_000,
    stops: tuple[str, ...] = ("SYD", "MEL", "ADL"),
) -> list[RowDict]:
    """Return joined active-route rows carrying one stop per row."""
    return [
        {
            "route_id": route_id,
            "departure_time": departure,
            "status": status,
            "truck_vehicle_id": truck_vehicle_id,
            "truck_capacity": truck_capacity,
            "stop_order": stop_order,
            "location_code": location,
        }
        for stop_order, location in enumerate(stops)
    ]


def _active_package_row(
    *,
    route_id: int = 21,
    package_id: int = 31,
    start_location: str = "SYD",
    end_location: str = "ADL",
    weight: Decimal = Decimal("250.50"),
) -> RowDict:
    """Return one valid active-route package row."""
    return {
        "route_id": route_id,
        "package_id": package_id,
        "start_location": start_location,
        "end_location": end_location,
        "weight": weight,
    }


class FleetOverviewCountMapperShould(unittest.TestCase):
    """Validate scalar aggregate row mapping and projection invariants."""

    def test_maps_package_counts(self) -> None:
        overview = map_package_overview(_package_count_row())

        self.assertEqual(overview.by_status.todo, 3)
        self.assertEqual(overview.by_status.in_progress, 2)
        self.assertEqual(overview.by_status.done, 1)
        self.assertEqual(overview.unassigned, 2)
        self.assertEqual(overview.past_due, 1)

    def test_rejects_invalid_package_counts_and_cross_count_invariants(self) -> None:
        for field, value, error in (
            ("todo", True, TypeError),
            ("in_progress", -1, ValueError),
            ("unassigned", "2", TypeError),
            ("past_due", -1, ValueError),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(error):
                map_package_overview(_package_count_row(**{field: value}))

        with self.assertRaisesRegex(ValueError, "unassigned cannot exceed"):
            map_package_overview(_package_count_row(unassigned=7))
        with self.assertRaisesRegex(ValueError, "past_due cannot exceed"):
            map_package_overview(_package_count_row(past_due=6))

    def test_maps_truck_counts(self) -> None:
        overview = map_truck_overview(_truck_count_row())

        self.assertEqual(overview.by_status.free, 2)
        self.assertEqual(overview.by_status.on_the_way, 1)
        self.assertEqual(overview.unknown_location, 1)

    def test_rejects_invalid_truck_counts_and_cross_count_invariants(self) -> None:
        for field, value, error in (
            ("free", True, TypeError),
            ("on_the_way", -1, ValueError),
            ("unknown_location", "1", TypeError),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(error):
                map_truck_overview(_truck_count_row(**{field: value}))

        with self.assertRaisesRegex(ValueError, "unknown_location cannot exceed"):
            map_truck_overview(_truck_count_row(unknown_location=4))

    def test_missing_aggregate_column_propagates_key_error(self) -> None:
        row = _package_count_row()
        del row["todo"]

        with self.assertRaises(KeyError):
            map_package_overview(row)


class RouteOverviewMapperShould(unittest.TestCase):
    """Validate past-due candidate parsing and final-ETA calculations."""

    def test_maps_status_counts_and_uses_strict_final_eta_boundary(self) -> None:
        travel_time = _schedule().eta_final - DEPARTURE
        generated_at = datetime(2030, 2, 1, 12, 0)
        overdue_departure = generated_at - travel_time - timedelta(microseconds=1)
        exact_departure = generated_at - travel_time
        candidates = [
            _candidate(
                route_id=22,
                departure=exact_departure,
                stops=[
                    {"stop_order": 2, "location_code": "ADL"},
                    {"stop_order": 0, "location_code": "SYD"},
                    {"stop_order": 1, "location_code": "MEL"},
                ],
            ),
            _candidate(route_id=21, departure=overdue_departure),
        ]

        overview = map_route_overview(_route_count_row(candidates=candidates), generated_at)

        self.assertEqual(overview.by_status.total, 5)
        self.assertEqual(overview.past_due, 1)

    def test_accepts_empty_candidate_array(self) -> None:
        overview = map_route_overview(_route_count_row(), DEPARTURE)

        self.assertEqual(overview.past_due, 0)

    def test_rejects_aware_generated_at_and_candidate_departure(self) -> None:
        with self.assertRaisesRegex(ValueError, "generated_at must be timezone-naive"):
            map_route_overview(_route_count_row(), DEPARTURE.replace(tzinfo=UTC))

        candidate = _candidate(route_id=21, departure=DEPARTURE.replace(tzinfo=UTC))
        with self.assertRaisesRegex(ValueError, "departure_time must be timezone-naive"):
            map_route_overview(_route_count_row(candidates=[candidate]), DEPARTURE)

    def test_rejects_invalid_candidate_container_shapes(self) -> None:
        invalid_values = cast(
            "tuple[object, ...]",
            (
                {},
                [1],
                [
                    {
                        "route_id": 21,
                        "departure_time": DEPARTURE.isoformat(),
                        "stops": {},
                    }
                ],
                [
                    {
                        "route_id": 21,
                        "departure_time": DEPARTURE.isoformat(),
                        "stops": [1],
                    }
                ],
            ),
        )
        for candidates in invalid_values:
            with self.subTest(candidates=candidates), self.assertRaises(TypeError):
                map_route_overview(_route_count_row(candidates=candidates), DEPARTURE)

    def test_rejects_invalid_departure_text_and_non_contiguous_stop_orders(self) -> None:
        invalid_time = _candidate(route_id=21, departure=DEPARTURE)
        invalid_time["departure_time"] = "not-a-datetime"
        with self.assertRaisesRegex(ValueError, "valid ISO 8601"):
            map_route_overview(_route_count_row(candidates=[invalid_time]), DEPARTURE)

        invalid_stops = _candidate(
            route_id=21,
            departure=DEPARTURE,
            stops=[
                {"stop_order": 0, "location_code": "SYD"},
                {"stop_order": 2, "location_code": "MEL"},
            ],
        )
        with self.assertRaisesRegex(ValueError, "contiguous from zero"):
            map_route_overview(_route_count_row(candidates=[invalid_stops]), DEPARTURE)


class ActiveRouteOverviewMapperShould(unittest.TestCase):
    """Validate route reconstruction, positions, load metrics, and ordering."""

    def test_maps_in_transit_route_with_truck_and_maximum_segment_load(self) -> None:
        rows = _active_route_rows()
        packages = [
            _active_package_row(package_id=31, weight=Decimal("250.50")),
            _active_package_row(
                package_id=32,
                start_location="MEL",
                end_location="ADL",
                weight=Decimal("100.25"),
            ),
        ]

        overview = map_active_route_overview(rows, packages, generated_at=DEPARTURE)

        self.assertIsNotNone(overview)
        assert overview is not None
        self.assertEqual(overview.route_id, 21)
        self.assertEqual(overview.status, RouteStatus.IN_PROGRESS)
        self.assertEqual(overview.start_location, SYD)
        self.assertEqual(overview.end_location, ADL)
        self.assertIsInstance(overview.position, InTransitPosition)
        self.assertEqual(overview.assigned_package_count, 2)
        self.assertIsNotNone(overview.truck)
        assert overview.truck is not None
        self.assertEqual(overview.truck.truck_id, 1001)
        self.assertEqual(overview.maximum_segment_load, 350.75)
        self.assertEqual(overview.capacity_utilization_percent, 35.075)

    def test_maps_intermediate_and_final_stop_boundaries(self) -> None:
        schedule = _schedule()

        intermediate = map_active_route_overview(
            _active_route_rows(),
            [],
            generated_at=schedule.arrival_time_at(MEL),
        )
        final = map_active_route_overview(
            _active_route_rows(),
            [],
            generated_at=schedule.eta_final,
        )

        self.assertIsNotNone(intermediate)
        self.assertIsNotNone(final)
        assert intermediate is not None and final is not None
        self.assertEqual(
            intermediate.position,
            AtStopPosition(stop_location=MEL, next_eta=schedule.eta_final),
        )
        self.assertEqual(final.position, AtStopPosition(stop_location=ADL, next_eta=None))

    def test_discards_route_after_final_eta(self) -> None:
        result = map_active_route_overview(
            _active_route_rows(),
            [],
            generated_at=_schedule().eta_final + timedelta(microseconds=1),
        )

        self.assertIsNone(result)

    def test_maps_route_without_truck_or_packages(self) -> None:
        overview = map_active_route_overview(
            _active_route_rows(truck_vehicle_id=None, truck_capacity=None),
            [],
            generated_at=DEPARTURE,
        )

        self.assertIsNotNone(overview)
        assert overview is not None
        self.assertIsNone(overview.truck)
        self.assertEqual(overview.assigned_package_count, 0)
        self.assertEqual(overview.maximum_segment_load, 0.0)
        self.assertIsNone(overview.capacity_utilization_percent)

    def test_rejects_empty_or_inconsistent_route_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "without route rows"):
            map_active_route_overview([], [], generated_at=DEPARTURE)

        rows = _active_route_rows()
        rows[1]["status"] = RouteStatus.SCHEDULED.value
        with self.assertRaisesRegex(ValueError, "inconsistent route metadata"):
            map_active_route_overview(rows, [], generated_at=DEPARTURE)

    def test_rejects_partial_truck_metadata(self) -> None:
        for truck_id, capacity in ((1001, None), (None, 1_000)):
            with (
                self.subTest(truck_id=truck_id, capacity=capacity),
                self.assertRaisesRegex(ValueError, "inconsistent truck metadata"),
            ):
                map_active_route_overview(
                    _active_route_rows(
                        truck_vehicle_id=truck_id,
                        truck_capacity=capacity,
                    ),
                    [],
                    generated_at=DEPARTURE,
                )

    def test_sorts_stops_and_rejects_duplicate_or_gapped_orders(self) -> None:
        rows = list(reversed(_active_route_rows()))
        overview = map_active_route_overview(rows, [], generated_at=DEPARTURE)
        self.assertIsNotNone(overview)
        assert overview is not None
        self.assertEqual((overview.start_location, overview.end_location), (SYD, ADL))

        for orders in ((0, 0, 1), (0, 2, 3)):
            invalid_rows = _active_route_rows()
            for row, order in zip(invalid_rows, orders, strict=True):
                row["stop_order"] = order
            with self.subTest(orders=orders), self.assertRaisesRegex(ValueError, "contiguous from zero"):
                map_active_route_overview(invalid_rows, [], generated_at=DEPARTURE)

    def test_rejects_wrong_route_and_duplicate_package_rows(self) -> None:
        wrong_route = _active_package_row(route_id=22)
        with self.assertRaisesRegex(ValueError, "belongs to route 22"):
            map_active_route_overview(
                _active_route_rows(),
                [wrong_route],
                generated_at=DEPARTURE,
            )

        duplicate = _active_package_row()
        with self.assertRaisesRegex(ValueError, "duplicate package rows"):
            map_active_route_overview(
                _active_route_rows(),
                [duplicate, duplicate.copy()],
                generated_at=DEPARTURE,
            )

    def test_rejects_package_path_that_is_absent_or_reversed(self) -> None:
        for package in (
            _active_package_row(start_location="PER", end_location="ADL"),
            _active_package_row(start_location="ADL", end_location="SYD"),
        ):
            with self.subTest(package=package), self.assertRaisesRegex(ValueError, "does not follow"):
                map_active_route_overview(
                    _active_route_rows(),
                    [package],
                    generated_at=DEPARTURE,
                )

    def test_rejects_invalid_package_weights(self) -> None:
        for weight, error in (
            (1, TypeError),
            (Decimal("0"), ValueError),
            (Decimal("-1"), ValueError),
            (Decimal("NaN"), ValueError),
            (Decimal("Infinity"), ValueError),
        ):
            with self.subTest(weight=weight), self.assertRaises(error):
                map_active_route_overview(
                    _active_route_rows(),
                    [_active_package_row(weight=weight)],  # type: ignore[arg-type]
                    generated_at=DEPARTURE,
                )

    def test_rejects_aware_times_and_unknown_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "generated_at must be timezone-naive"):
            map_active_route_overview(
                _active_route_rows(),
                [],
                generated_at=DEPARTURE.replace(tzinfo=UTC),
            )

        with self.assertRaisesRegex(ValueError, "departure_time must be timezone-naive"):
            map_active_route_overview(
                _active_route_rows(departure=DEPARTURE.replace(tzinfo=UTC)),
                [],
                generated_at=DEPARTURE,
            )

        with self.assertRaises(ValueError):
            map_active_route_overview(
                _active_route_rows(status="UNKNOWN"),
                [],
                generated_at=DEPARTURE,
            )

    @patch(f"{MODULE}.RouteScheduler.build")
    def test_rejects_malformed_active_positions(self, build_mock: MagicMock) -> None:
        schedule = MagicMock()
        build_mock.return_value = schedule

        for position in (
            RoutePosition(kind=RoutePositionKind.AT_STOP),
            RoutePosition(kind=RoutePositionKind.IN_TRANSIT, from_city=SYD),
        ):
            schedule.position_at.return_value = position
            with self.subTest(kind=position.kind), self.assertRaises(RuntimeError):
                map_active_route_overview(
                    _active_route_rows(),
                    [],
                    generated_at=DEPARTURE,
                )

    def test_groups_orders_limits_and_places_missing_eta_last(self) -> None:
        generated_at = _schedule().eta_final
        first = _active_route_rows(route_id=22, departure=generated_at)
        second = _active_route_rows(route_id=21, departure=generated_at)
        final_stop = _active_route_rows(route_id=20)

        result = map_active_route_overviews(
            [*first, *second, *final_stop],
            [
                _active_package_row(route_id=22, package_id=32),
                _active_package_row(route_id=21, package_id=31),
            ],
            generated_at=generated_at,
            active_route_limit=3,
        )

        self.assertEqual([route.route_id for route in result], [21, 22, 20])
        self.assertEqual([route.assigned_package_count for route in result], [1, 1, 0])

        limited = map_active_route_overviews(
            [*first, *second, *final_stop],
            [],
            generated_at=generated_at,
            active_route_limit=2,
        )
        self.assertEqual([route.route_id for route in limited], [21, 22])

    def test_rejects_packages_for_unknown_routes(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing active routes: 99"):
            map_active_route_overviews(
                _active_route_rows(),
                [_active_package_row(route_id=99)],
                generated_at=DEPARTURE,
                active_route_limit=10,
            )

    def test_rejects_invalid_limit_even_for_empty_rows(self) -> None:
        for limit, error in ((True, TypeError), (0, ValueError), (101, ValueError)):
            with self.subTest(limit=limit), self.assertRaises(error):
                map_active_route_overviews(
                    [],
                    [],
                    generated_at=DEPARTURE,
                    active_route_limit=limit,  # type: ignore[arg-type]
                )

    def test_returns_empty_tuple_for_empty_rows(self) -> None:
        self.assertEqual(
            map_active_route_overviews(
                [],
                [],
                generated_at=DEPARTURE,
                active_route_limit=10,
            ),
            (),
        )
