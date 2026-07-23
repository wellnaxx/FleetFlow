"""PostgreSQL implementation of the fleet-overview output port."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from psycopg import IsolationLevel

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driven.persistence.database.executor import fetch_all_tx, fetch_one_tx, transaction_cursor
from src.adapters.driven.persistence.database.mappers.fleet_overview import (
    map_active_route_overviews,
    map_package_overview,
    map_route_overview,
    map_truck_overview,
    select_active_route_overviews,
)
from src.adapters.driven.persistence.database.queries import QUERIES
from src.application.results.fleet_overview import ActiveRouteOverview, FleetOverview
from src.shared.validation import require_datetime, require_positive_int

if TYPE_CHECKING:
    from datetime import datetime

    from psycopg import Cursor

    from src.adapters.driven.persistence.database.executor import Row

logger = logging.getLogger(__name__)

_ACTIVE_ROUTE_CANDIDATE_BATCH_SIZE = 100
_ACTIVE_ROUTE_ROW_WARNING_THRESHOLD = 5_000


class PostgresFleetOverviewQuery:
    """Build fleet overviews from one repeatable-read database snapshot."""

    def get_overview(
        self,
        *,
        generated_at: datetime,
        active_route_limit: int,
    ) -> FleetOverview:
        """Return one coherent PostgreSQL-backed fleet overview.

        The aggregate and active-route queries run inside a read-only
        ``REPEATABLE READ`` transaction. This prevents counts and route detail
        rows from observing different committed database states during one
        overview request.

        Args:
            generated_at: Timezone-naive app-local business time used for all
                deadline and route-position calculations.
            active_route_limit: Maximum active routes to return, from 1
                through 100.

        Returns:
            Validated fleet counts and ordered active-route projections.

        Raises:
            TypeError: If either argument or a returned row value has an
                invalid runtime type.
            ValueError: If an argument is outside its supported range or
                returned data violates an overview invariant.
            DatabaseError: If an aggregate query returns no row or database
                execution fails.
            DomainValidationError: If persisted route topology is invalid.
            EntityNotFoundError: If a persisted route segment has no map
                distance.
            RuntimeError: If an active route position lacks required fields.
        """
        generated_at = require_datetime(generated_at, "generated_at")
        if generated_at.tzinfo is not None and generated_at.utcoffset() is not None:
            raise ValueError("generated_at must be timezone-naive.")

        active_route_limit = require_positive_int(active_route_limit, "active_route_limit")
        if active_route_limit > 100:
            raise ValueError("active_route_limit must be less than or equal to 100.")

        with transaction_cursor(isolation_level=IsolationLevel.REPEATABLE_READ, read_only=True) as cursor:
            package_counts_row = fetch_one_tx(cursor, QUERIES.fleet_overview.package_counts, (generated_at,))
            route_counts_row = fetch_one_tx(cursor, QUERIES.fleet_overview.route_counts, (generated_at,))
            truck_counts_row = fetch_one_tx(cursor, QUERIES.fleet_overview.truck_counts)

            if package_counts_row is None:
                raise DatabaseError.missing_query_row("Fleet overview package count")
            if route_counts_row is None:
                raise DatabaseError.missing_query_row("Fleet overview route count")
            if truck_counts_row is None:
                raise DatabaseError.missing_query_row("Fleet overview truck count")

            active_route_overviews = self._load_active_route_overviews(
                cursor,
                generated_at=generated_at,
                active_route_limit=active_route_limit,
            )

        package_overview = map_package_overview(package_counts_row)
        route_overview = map_route_overview(route_counts_row, generated_at)
        truck_overview = map_truck_overview(truck_counts_row)

        return FleetOverview(
            generated_at=generated_at,
            packages=package_overview,
            routes=route_overview,
            trucks=truck_overview,
            active_routes=active_route_overviews,
        )

    @staticmethod
    def _load_active_route_overviews(
        cursor: Cursor[Row],
        *,
        generated_at: datetime,
        active_route_limit: int,
    ) -> tuple[ActiveRouteOverview, ...]:
        """Load and map active routes in bounded keyset-paginated batches.

        Package rows are fetched only for route ids in the current candidate
        page. Each page and the accumulated selection retain at most the
        requested top N projections, keeping application memory bounded while
        still evaluating every candidate for exact ETA-based ordering.

        Args:
            cursor: Cursor in the overview's repeatable-read transaction.
            generated_at: Timezone-naive app-local evaluation time.
            active_route_limit: Maximum number of final projections.

        Returns:
            Globally ordered active-route projections.

        Raises:
            DatabaseError: If keyset pagination fails to advance.
            TypeError: If a returned route id has an invalid runtime type.
            ValueError: If returned route, stop, package, or schedule data is
                invalid.
            RuntimeError: If an active route position lacks required fields.
        """
        selected: tuple[ActiveRouteOverview, ...] = ()
        after_route_id = 0
        batch_number = 0

        while True:
            route_rows = fetch_all_tx(
                cursor,
                QUERIES.fleet_overview.active_routes,
                (
                    generated_at,
                    after_route_id,
                    _ACTIVE_ROUTE_CANDIDATE_BATCH_SIZE,
                ),
            )
            if not route_rows:
                return selected

            route_ids = sorted({
                require_positive_int(route_row["route_id"], "route_id")
                for route_row in route_rows
            })
            next_after_route_id = route_ids[-1]
            if next_after_route_id <= after_route_id:
                raise DatabaseError("Active-route candidate pagination did not advance.")

            package_rows = fetch_all_tx(
                cursor,
                QUERIES.fleet_overview.active_route_packages,
                (route_ids,),
            )
            batch_number += 1
            _log_active_route_batch(
                batch_number=batch_number,
                candidate_count=len(route_ids),
                route_row_count=len(route_rows),
                package_row_count=len(package_rows),
            )

            batch_overviews = map_active_route_overviews(
                route_rows=route_rows,
                package_rows=package_rows,
                generated_at=generated_at,
                active_route_limit=active_route_limit,
            )
            selected = select_active_route_overviews(
                [*selected, *batch_overviews],
                generated_at=generated_at,
                active_route_limit=active_route_limit,
            )
            after_route_id = next_after_route_id


def _log_active_route_batch(
    *,
    batch_number: int,
    candidate_count: int,
    route_row_count: int,
    package_row_count: int,
) -> None:
    """Record bounded active-route fetch volumes and flag unusually large rows.

    Args:
        batch_number: One-based page number within the overview request.
        candidate_count: Distinct route candidates in the page.
        route_row_count: Joined stop rows returned for those candidates.
        package_row_count: Package rows returned for those candidates.
    """
    logger.debug(
        "Loaded active-route batch %d: candidates=%d stop_rows=%d package_rows=%d",
        batch_number,
        candidate_count,
        route_row_count,
        package_row_count,
    )
    if (
        route_row_count > _ACTIVE_ROUTE_ROW_WARNING_THRESHOLD
        or package_row_count > _ACTIVE_ROUTE_ROW_WARNING_THRESHOLD
    ):
        logger.warning(
            "Large active-route batch %d: candidates=%d stop_rows=%d package_rows=%d",
            batch_number,
            candidate_count,
            route_row_count,
            package_row_count,
        )
