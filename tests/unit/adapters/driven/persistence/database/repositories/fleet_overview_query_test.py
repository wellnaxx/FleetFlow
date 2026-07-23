"""Tests for the PostgreSQL fleet-overview query adapter."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, call, patch

from psycopg import IsolationLevel

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.fleet_overview_query import (
    PostgresFleetOverviewQuery,
)
from src.application.results.fleet_overview import (
    ActiveRouteOverview,
    FleetOverview,
    PackageOverview,
    RouteOverview,
    TruckOverview,
)

if TYPE_CHECKING:
    from src.adapters.driven.persistence.database.executor import RowDict

MODULE = "src.adapters.driven.persistence.database.repositories.fleet_overview_query"
GENERATED_AT = datetime(2030, 1, 1, 12, 0)


class PostgresFleetOverviewQueryShould(unittest.TestCase):
    """Validate transaction, SQL, mapping, and failure behavior."""

    def setUp(self) -> None:
        """Create the query and patch its persistence/mapping collaborators."""
        self.query = PostgresFleetOverviewQuery()
        self.cursor = MagicMock(name="cursor")

        self.transaction_cursor_mock = self._start_patch("transaction_cursor")
        self.fetch_one_tx_mock = self._start_patch("fetch_one_tx")
        self.fetch_all_tx_mock = self._start_patch("fetch_all_tx")
        self.map_package_overview_mock = self._start_patch("map_package_overview")
        self.map_route_overview_mock = self._start_patch("map_route_overview")
        self.map_truck_overview_mock = self._start_patch("map_truck_overview")
        self.map_active_route_overviews_mock = self._start_patch("map_active_route_overviews")
        self.select_active_route_overviews_mock = self._start_patch("select_active_route_overviews")

        self.transaction_cursor_mock.return_value.__enter__.return_value = self.cursor
        self.package_row: RowDict = {"todo": 0}
        self.route_row: RowDict = {"planned": 0}
        self.truck_row: RowDict = {"free": 0}
        self.fetch_one_tx_mock.side_effect = [
            self.package_row,
            self.route_row,
            self.truck_row,
        ]

        self.package_overview = cast(PackageOverview, MagicMock(name="package_overview"))
        self.route_overview = cast(RouteOverview, MagicMock(name="route_overview"))
        self.truck_overview = cast(TruckOverview, MagicMock(name="truck_overview"))
        self.active_routes = cast(
            "tuple[ActiveRouteOverview, ...]",
            (MagicMock(name="active_route"),),
        )
        self.map_package_overview_mock.return_value = self.package_overview
        self.map_route_overview_mock.return_value = self.route_overview
        self.map_truck_overview_mock.return_value = self.truck_overview
        self.map_active_route_overviews_mock.return_value = self.active_routes
        self.select_active_route_overviews_mock.return_value = self.active_routes

    def _start_patch(self, attribute: str) -> MagicMock:
        """Start and register cleanup for one module-level collaborator patch."""
        patcher = patch(f"{MODULE}.{attribute}")
        mocked = cast(MagicMock, patcher.start())
        self.addCleanup(patcher.stop)
        return mocked

    def test_builds_overview_from_one_repeatable_read_snapshot(self) -> None:
        """Run all reads in one snapshot and hand rows to the correct mappers."""
        active_rows: list[RowDict] = [
            {"route_id": 22},
            {"route_id": 21},
            {"route_id": 22},
        ]
        package_rows: list[RowDict] = [{"route_id": 21}]
        self.fetch_all_tx_mock.side_effect = [active_rows, package_rows, []]

        result = self.query.get_overview(
            generated_at=GENERATED_AT,
            active_route_limit=7,
        )

        self.assertEqual(
            result,
            FleetOverview(
                generated_at=GENERATED_AT,
                packages=self.package_overview,
                routes=self.route_overview,
                trucks=self.truck_overview,
                active_routes=self.active_routes,
            ),
        )
        self.transaction_cursor_mock.assert_called_once_with(
            isolation_level=IsolationLevel.REPEATABLE_READ,
            read_only=True,
        )
        self.assertEqual(
            self.fetch_one_tx_mock.call_args_list,
            [
                call(self.cursor, QUERIES.fleet_overview.package_counts, (GENERATED_AT,)),
                call(self.cursor, QUERIES.fleet_overview.route_counts, (GENERATED_AT,)),
                call(self.cursor, QUERIES.fleet_overview.truck_counts),
            ],
        )
        self.assertEqual(
            self.fetch_all_tx_mock.call_args_list,
            [
                call(
                    self.cursor,
                    QUERIES.fleet_overview.active_routes,
                    (GENERATED_AT, 0, 100),
                ),
                call(
                    self.cursor,
                    QUERIES.fleet_overview.active_route_packages,
                    ([21, 22],),
                ),
                call(
                    self.cursor,
                    QUERIES.fleet_overview.active_routes,
                    (GENERATED_AT, 22, 100),
                ),
            ],
        )
        self.map_package_overview_mock.assert_called_once_with(self.package_row)
        self.map_route_overview_mock.assert_called_once_with(self.route_row, GENERATED_AT)
        self.map_truck_overview_mock.assert_called_once_with(self.truck_row)
        self.map_active_route_overviews_mock.assert_called_once_with(
            route_rows=active_rows,
            package_rows=package_rows,
            generated_at=GENERATED_AT,
            active_route_limit=7,
        )
        self.select_active_route_overviews_mock.assert_called_once_with(
            [*self.active_routes],
            generated_at=GENERATED_AT,
            active_route_limit=7,
        )

    def test_skips_package_query_when_there_are_no_active_routes(self) -> None:
        """Avoid issuing ``ANY`` with an empty route-id collection."""
        self.fetch_all_tx_mock.return_value = []

        result = self.query.get_overview(
            generated_at=GENERATED_AT,
            active_route_limit=10,
        )

        self.assertIsInstance(result, FleetOverview)
        self.fetch_all_tx_mock.assert_called_once_with(
            self.cursor,
            QUERIES.fleet_overview.active_routes,
            (GENERATED_AT, 0, 100),
        )
        self.map_active_route_overviews_mock.assert_not_called()
        self.select_active_route_overviews_mock.assert_not_called()

    def test_rejects_missing_required_aggregate_rows(self) -> None:
        """Treat a missing aggregate row as a broken database query contract."""
        cases = (
            ([None, self.route_row, self.truck_row], "package count"),
            ([self.package_row, None, self.truck_row], "route count"),
            ([self.package_row, self.route_row, None], "truck count"),
        )

        for rows, message in cases:
            with self.subTest(message=message):
                self.fetch_one_tx_mock.reset_mock(side_effect=True)
                self.fetch_one_tx_mock.side_effect = rows
                self.fetch_all_tx_mock.reset_mock(side_effect=True)
                self.fetch_all_tx_mock.return_value = []

                with self.assertRaisesRegex(DatabaseError, message):
                    self.query.get_overview(
                        generated_at=GENERATED_AT,
                        active_route_limit=10,
                    )

    def test_rejects_invalid_generated_at_before_opening_transaction(self) -> None:
        """Validate runtime type and timezone convention before database work."""
        for value, error in (
            (cast(datetime, "2030-01-01"), TypeError),
            (GENERATED_AT.replace(tzinfo=UTC), ValueError),
        ):
            with self.subTest(value=value), self.assertRaises(error):
                self.query.get_overview(
                    generated_at=value,
                    active_route_limit=10,
                )

        self.transaction_cursor_mock.assert_not_called()

    def test_rejects_invalid_active_route_limits_before_opening_transaction(self) -> None:
        """Accept only positive integer limits no greater than one hundred."""
        for limit, error in ((True, TypeError), (0, ValueError), (-1, ValueError), (101, ValueError)):
            with self.subTest(limit=limit), self.assertRaises(error):
                self.query.get_overview(
                    generated_at=GENERATED_AT,
                    active_route_limit=limit,
                )

        self.transaction_cursor_mock.assert_not_called()

    def test_propagates_query_and_mapping_failures(self) -> None:
        """Do not replace adapter failures with partial overview results."""
        self.fetch_one_tx_mock.side_effect = DatabaseError("read failed")
        with self.assertRaisesRegex(DatabaseError, "read failed"):
            self.query.get_overview(
                generated_at=GENERATED_AT,
                active_route_limit=10,
            )

        self.fetch_one_tx_mock.side_effect = [
            self.package_row,
            self.route_row,
            self.truck_row,
        ]
        self.fetch_all_tx_mock.return_value = []
        self.map_package_overview_mock.side_effect = ValueError("invalid count")
        with self.assertRaisesRegex(ValueError, "invalid count"):
            self.query.get_overview(
                generated_at=GENERATED_AT,
                active_route_limit=10,
            )

    def test_merges_multiple_candidate_pages_without_losing_global_ordering(self) -> None:
        """Retain the global top N while discarding noncompetitive page rows."""
        first_rows: list[RowDict] = [{"route_id": 10}]
        first_packages: list[RowDict] = [{"route_id": 10}]
        second_rows: list[RowDict] = [{"route_id": 20}]
        second_packages: list[RowDict] = [{"route_id": 20}]
        first_overview = cast(ActiveRouteOverview, MagicMock(name="first_overview"))
        second_overview = cast(ActiveRouteOverview, MagicMock(name="second_overview"))
        self.fetch_all_tx_mock.side_effect = [
            first_rows,
            first_packages,
            second_rows,
            second_packages,
            [],
        ]
        self.map_active_route_overviews_mock.side_effect = [
            (first_overview,),
            (second_overview,),
        ]
        self.select_active_route_overviews_mock.side_effect = [
            (first_overview,),
            (second_overview, first_overview),
        ]

        result = self.query.get_overview(
            generated_at=GENERATED_AT,
            active_route_limit=2,
        )

        self.assertEqual(result.active_routes, (second_overview, first_overview))
        self.assertEqual(
            self.fetch_all_tx_mock.call_args_list,
            [
                call(
                    self.cursor,
                    QUERIES.fleet_overview.active_routes,
                    (GENERATED_AT, 0, 100),
                ),
                call(
                    self.cursor,
                    QUERIES.fleet_overview.active_route_packages,
                    ([10],),
                ),
                call(
                    self.cursor,
                    QUERIES.fleet_overview.active_routes,
                    (GENERATED_AT, 10, 100),
                ),
                call(
                    self.cursor,
                    QUERIES.fleet_overview.active_route_packages,
                    ([20],),
                ),
                call(
                    self.cursor,
                    QUERIES.fleet_overview.active_routes,
                    (GENERATED_AT, 20, 100),
                ),
            ],
        )
        self.assertEqual(
            self.select_active_route_overviews_mock.call_args_list,
            [
                call(
                    [first_overview],
                    generated_at=GENERATED_AT,
                    active_route_limit=2,
                ),
                call(
                    [first_overview, second_overview],
                    generated_at=GENERATED_AT,
                    active_route_limit=2,
                ),
            ],
        )

    @patch(f"{MODULE}._ACTIVE_ROUTE_ROW_WARNING_THRESHOLD", 1)
    @patch(f"{MODULE}.logger")
    def test_monitors_and_warns_about_large_bounded_batches(
        self,
        logger_mock: MagicMock,
    ) -> None:
        """Log every page and warn when joined row volume crosses its guardrail."""
        route_rows: list[RowDict] = [{"route_id": 21}, {"route_id": 21}]
        self.fetch_all_tx_mock.side_effect = [route_rows, [], []]

        self.query.get_overview(
            generated_at=GENERATED_AT,
            active_route_limit=10,
        )

        logger_mock.debug.assert_called_once_with(
            "Loaded active-route batch %d: candidates=%d stop_rows=%d package_rows=%d",
            1,
            1,
            2,
            0,
        )
        logger_mock.warning.assert_called_once_with(
            "Large active-route batch %d: candidates=%d stop_rows=%d package_rows=%d",
            1,
            1,
            2,
            0,
        )

    def test_rejects_candidate_page_that_does_not_advance_keyset(self) -> None:
        """Fail instead of looping when returned route ids violate the SQL contract."""
        self.fetch_all_tx_mock.side_effect = [
            [{"route_id": 21}],
            [],
            [{"route_id": 21}],
        ]

        with self.assertRaisesRegex(DatabaseError, "did not advance"):
            self.query.get_overview(
                generated_at=GENERATED_AT,
                active_route_limit=10,
            )
