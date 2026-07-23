"""Map PostgreSQL fleet-overview rows into application result projections.

The count queries return scalar aggregate rows, while active-route queries
return repeated route metadata joined to ordered stops and separate package
load rows. This module validates those persistence shapes, reconstructs the
domain scheduling inputs needed for temporal calculations, and exposes only
read-only application projections to callers.

All route timestamps are timezone-naive app-local business times. Invalid or
inconsistent database rows are rejected at this adapter boundary rather than
being allowed to produce a misleading overview.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from heapq import nsmallest
from typing import TypedDict, cast

from src.adapters.driven.persistence.database.executor import RowDict
from src.adapters.driven.persistence.database.validation import require_count
from src.application.results.fleet_overview import (
    ActiveRouteOverview,
    ActiveRoutePosition,
    AssignedTruckOverview,
    AtStopPosition,
    InTransitPosition,
    PackageOverview,
    PackageStatusCounts,
    RouteOverview,
    RouteStatusCounts,
    TruckOverview,
    TruckStatusCounts,
)
from src.domain.enums.route_status import RouteStatus
from src.domain.services.route_load_calculator import RouteLoadCalculator
from src.domain.services.route_scheduler import RouteScheduler
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.package_load import PackageLoad
from src.domain.value_objects.route_path import RoutePath
from src.domain.value_objects.route_schedule import RoutePosition, RoutePositionKind
from src.shared.validation import (
    require_datetime,
    require_finite_positive_decimal,
    require_non_negative_int,
    require_optional_positive_int,
    require_positive_int,
    require_str,
)


class PackageOverviewRow(TypedDict):
    """Validated aggregate columns returned by the package-count query."""

    todo: int
    in_progress: int
    done: int
    unassigned: int
    past_due: int


def map_package_overview(row: RowDict) -> PackageOverview:
    """Map one package-count aggregate row.

    Args:
        row: Raw database row containing lifecycle and operational counts.

    Returns:
        Validated package overview projection.

    Raises:
        KeyError: If a required query column is absent.
        TypeError: If a count is not an integer or is a boolean.
        ValueError: If a count is negative or violates overview invariants.
    """
    typed = _as_package_overview_row(row)

    return PackageOverview(
        by_status=PackageStatusCounts(
            todo=typed["todo"],
            in_progress=typed["in_progress"],
            done=typed["done"],
        ),
        unassigned=typed["unassigned"],
        past_due=typed["past_due"],
    )


def _as_package_overview_row(row: RowDict) -> PackageOverviewRow:
    """Validate and narrow a raw package-count row."""
    todo = require_count(row["todo"], "todo")
    in_progress = require_count(row["in_progress"], "in_progress")
    done = require_count(row["done"], "done")
    unassigned = require_count(row["unassigned"], "unassigned")
    past_due = require_count(row["past_due"], "past_due")

    return PackageOverviewRow(
        todo=todo,
        in_progress=in_progress,
        done=done,
        unassigned=unassigned,
        past_due=past_due,
    )


class PastDueRouteStopJSON(TypedDict):
    """JSON representation of one ordered stop in a route candidate."""

    stop_order: int
    location_code: str


class PastDueRouteCandidateJSON(TypedDict):
    """JSON representation of one route requiring final-ETA evaluation."""

    route_id: int
    departure_time: str
    stops: list[PastDueRouteStopJSON]


class RouteOverviewRow(TypedDict):
    """Validated aggregate columns returned by the route-count query."""

    planned: int
    scheduled: int
    in_progress: int
    completed: int
    past_due_candidates: list[PastDueRouteCandidateJSON]


@dataclass(frozen=True, slots=True)
class PastDueRouteCandidate:
    """Normalized scheduling inputs for one possible past-due route."""

    route_id: int
    departure_time: datetime
    path: RoutePath


def map_route_overview(row: RowDict, generated_at: datetime) -> RouteOverview:
    """Map route counts and calculate the exact past-due route count.

    PostgreSQL performs only coarse candidate selection. Final ETAs are
    calculated with the domain scheduler so this adapter uses the same timing
    rules as the rest of the application. A route is past due only when its
    final ETA is strictly earlier than ``generated_at``.

    Args:
        row: Raw aggregate row containing status counts and JSON candidates.
        generated_at: Timezone-naive app-local evaluation time.

    Returns:
        Validated route overview projection.

    Raises:
        KeyError: If a required aggregate or candidate field is absent.
        TypeError: If a count or JSON value has an invalid runtime type.
        ValueError: If counts, timestamps, stop orders, or locations are
            invalid.
        DomainValidationError: If candidate route topology is invalid.
        EntityNotFoundError: If a candidate segment has no map distance.
    """
    generated_at = _require_naive_datetime(generated_at, "generated_at")
    typed = _as_route_overview_row(row)

    return RouteOverview(
        by_status=RouteStatusCounts(
            planned=typed["planned"],
            scheduled=typed["scheduled"],
            in_progress=typed["in_progress"],
            completed=typed["completed"],
        ),
        past_due=sum(
            RouteScheduler.build(
                locations=candidate.path.locations,
                departure_time=candidate.departure_time,
            ).eta_final
            < generated_at
            for candidate in (
                _map_past_due_candidate(raw_candidate) for raw_candidate in typed["past_due_candidates"]
            )
        ),
    )


def _as_route_overview_row(row: RowDict) -> RouteOverviewRow:
    """Validate and narrow a raw route-count aggregate row."""
    planned = require_count(row["planned"], "planned")
    scheduled = require_count(row["scheduled"], "scheduled")
    in_progress = require_count(row["in_progress"], "in_progress")
    completed = require_count(row["completed"], "completed")
    past_due_candidates = _as_past_due_route_candidates(row["past_due_candidates"])

    return RouteOverviewRow(
        planned=planned,
        scheduled=scheduled,
        in_progress=in_progress,
        completed=completed,
        past_due_candidates=past_due_candidates,
    )


def _as_past_due_route_candidates(value: object) -> list[PastDueRouteCandidateJSON]:
    """Validate and narrow the JSON array of past-due route candidates."""
    if not isinstance(value, list):
        raise TypeError("past_due_candidates must be a JSON array.")

    candidates = cast("list[object]", value)
    return [_as_past_due_candidate(candidate) for candidate in candidates]


def _as_past_due_candidate(value: object) -> PastDueRouteCandidateJSON:
    """Validate and narrow one raw past-due route candidate object."""
    if not isinstance(value, dict):
        raise TypeError("Each past-due candidate must be a JSON object.")

    candidate = cast("dict[object, object]", value)

    return PastDueRouteCandidateJSON(
        route_id=require_positive_int(candidate["route_id"], "route_id"),
        departure_time=require_str(candidate["departure_time"], "departure_time"),
        stops=_as_candidate_stops(candidate["stops"]),
    )


def _as_candidate_stops(value: object) -> list[PastDueRouteStopJSON]:
    """Validate and narrow one candidate's JSON stop array."""
    if not isinstance(value, list):
        raise TypeError("Past-due candidate's stops must be a JSON array.")

    candidates = cast("list[object]", value)
    return [_as_candidate_stop(candidate) for candidate in candidates]


def _as_candidate_stop(value: object) -> PastDueRouteStopJSON:
    """Validate and narrow one raw candidate stop object."""
    if not isinstance(value, dict):
        raise TypeError("Each stop must be a JSON object.")

    candidate = cast("dict[object, object]", value)

    return PastDueRouteStopJSON(
        stop_order=require_non_negative_int(candidate["stop_order"], "stop_order"),
        location_code=require_str(candidate["location_code"], "location_code"),
    )


def _map_past_due_candidate(candidate: PastDueRouteCandidateJSON) -> PastDueRouteCandidate:
    """Normalize one validated JSON candidate into scheduling inputs.

    Stops are sorted by their explicit order because JSON array ordering is
    not trusted as a persistence invariant.
    """
    ordered_stops = sorted(
        candidate["stops"],
        key=lambda stop: stop["stop_order"],
    )

    stop_orders = [stop["stop_order"] for stop in ordered_stops]
    if stop_orders != list(range(len(ordered_stops))):
        raise ValueError(f"Route {candidate['route_id']} stop orders must be contiguous from zero.")

    return PastDueRouteCandidate(
        route_id=candidate["route_id"],
        departure_time=_parse_naive_datetime(
            candidate["departure_time"],
            f"route {candidate['route_id']} departure_time",
        ),
        path=RoutePath.create(*(stop["location_code"] for stop in ordered_stops)),
    )


class TruckOverviewRow(TypedDict):
    """Validated aggregate columns returned by the truck-count query."""

    free: int
    on_the_way: int
    unknown_location: int


def map_truck_overview(row: RowDict) -> TruckOverview:
    """Map one truck-count aggregate row.

    Args:
        row: Raw database row containing status and location counts.

    Returns:
        Validated truck overview projection.

    Raises:
        KeyError: If a required query column is absent.
        TypeError: If a count is not an integer or is a boolean.
        ValueError: If a count is negative or violates overview invariants.
    """
    typed = _as_truck_overview_row(row)

    return TruckOverview(
        by_status=TruckStatusCounts(
            free=typed["free"],
            on_the_way=typed["on_the_way"],
        ),
        unknown_location=typed["unknown_location"],
    )


def _as_truck_overview_row(row: RowDict) -> TruckOverviewRow:
    """Validate and narrow a raw truck-count row."""
    free = require_count(row["free"], "free")
    on_the_way = require_count(row["on_the_way"], "on_the_way")
    unknown_location = require_count(row["unknown_location"], "unknown_location")

    return TruckOverviewRow(
        free=free,
        on_the_way=on_the_way,
        unknown_location=unknown_location,
    )


class ActiveRouteRow(TypedDict):
    """Route metadata repeated across active-route stop rows."""

    route_id: int
    departure_time: datetime
    status: str
    truck_vehicle_id: int | None
    truck_capacity: int | None


class ActiveRouteStopRow(TypedDict):
    """Validated stop columns from one active-route row."""

    stop_order: int
    location_code: str


class ActiveRoutePackageRow(TypedDict):
    """Validated package-load columns associated with an active route."""

    route_id: int
    package_id: int
    start_location: str
    end_location: str
    weight: Decimal


def map_active_route_overviews(
    route_rows: list[RowDict],
    package_rows: list[RowDict],
    *,
    generated_at: datetime,
    active_route_limit: int,
) -> tuple[ActiveRouteOverview, ...]:
    """Map, order, and limit active-route projections.

    Rows are grouped by route id before each route is reconstructed. Routes
    whose calculated position is no longer active are discarded. Remaining
    routes are ordered by next ETA, with unknown next ETAs last and route id as
    the stable tie-breaker.

    Args:
        route_rows: Repeated route metadata and one stop per database row.
        package_rows: Package loads for the selected active route ids.
        generated_at: Timezone-naive app-local position evaluation time.
        active_route_limit: Maximum number of projections, from 1 through 100.

    Returns:
        Ordered tuple containing at most ``active_route_limit`` active routes.

    Raises:
        KeyError: If a required database column is absent.
        TypeError: If a row value has an invalid runtime type.
        ValueError: If time, limit, route ownership, metadata, stop order, or
            persisted enum values are invalid.
        DomainValidationError: If route or package topology is invalid.
        EntityNotFoundError: If a route segment has no map distance.
        RuntimeError: If an active schedule position lacks required fields.
    """
    generated_at = _require_naive_datetime(generated_at, "generated_at")
    active_route_limit = require_positive_int(active_route_limit, "active_route_limit")
    if active_route_limit > 100:
        raise ValueError("active_route_limit must be less than or equal to 100.")

    route_groups = _group_rows_by_route_id(route_rows)
    package_groups = _group_rows_by_route_id(package_rows)

    unknown_package_route_ids = package_groups.keys() - route_groups.keys()
    if unknown_package_route_ids:
        route_ids = ", ".join(str(route_id) for route_id in sorted(unknown_package_route_ids))
        raise ValueError(f"Package rows reference missing active routes: {route_ids}.")

    active_routes: list[ActiveRouteOverview] = []

    for route_id in sorted(route_groups):
        overview = map_active_route_overview(
            route_groups[route_id],
            package_groups.get(route_id, []),
            generated_at=generated_at,
        )

        if overview is not None:
            active_routes.append(overview)

    return select_active_route_overviews(
        active_routes,
        generated_at=generated_at,
        active_route_limit=active_route_limit,
    )


def select_active_route_overviews(
    active_routes: list[ActiveRouteOverview] | tuple[ActiveRouteOverview, ...],
    *,
    generated_at: datetime,
    active_route_limit: int,
) -> tuple[ActiveRouteOverview, ...]:
    """Select the globally ordered top active-route projections.

    This operation is safe to apply repeatedly while merging independently
    mapped candidate batches: an item outside one batch's top N cannot enter
    the final global top N.

    Args:
        active_routes: Already mapped active-route projections.
        generated_at: Timezone-naive app-local position evaluation time.
        active_route_limit: Maximum number of projections, from 1 through 100.

    Returns:
        Routes ordered by known next ETA, then route id, with missing next ETAs
        ordered last.

    Raises:
        TypeError: If an argument has an invalid runtime type.
        ValueError: If ``generated_at`` is timezone-aware or the limit is
            outside 1 through 100.
    """
    generated_at = _require_naive_datetime(generated_at, "generated_at")
    active_route_limit = require_positive_int(active_route_limit, "active_route_limit")
    if active_route_limit > 100:
        raise ValueError("active_route_limit must be less than or equal to 100.")

    return tuple(
        nsmallest(
            active_route_limit,
            active_routes,
            key=lambda route: (
                route.position.next_eta is None,
                route.position.next_eta or generated_at,
                route.route_id,
            ),
        )
    )


def _group_rows_by_route_id(
    rows: list[RowDict],
) -> dict[int, list[RowDict]]:
    """Group raw rows by a validated positive ``route_id`` column."""
    grouped: dict[int, list[RowDict]] = {}

    for row in rows:
        route_id = require_positive_int(row["route_id"], "route_id")
        grouped.setdefault(route_id, []).append(row)

    return grouped


def map_active_route_overview(
    route_rows: list[RowDict],
    package_rows: list[RowDict],
    *,
    generated_at: datetime,
) -> ActiveRouteOverview | None:
    """Map all persistence rows belonging to one active-route candidate.

    Args:
        route_rows: Rows for exactly one route, each carrying one stop and
            identical route/truck metadata.
        package_rows: Zero or more package load rows owned by that route.
        generated_at: Timezone-naive app-local position evaluation time.

    Returns:
        Active-route projection, or ``None`` when scheduling shows that the
        route has already passed its final stop.

    Raises:
        KeyError: If a required database column is absent.
        TypeError: If a row value has an invalid runtime type.
        ValueError: If rows are empty or contain inconsistent metadata,
            invalid stop ordering, duplicate packages, wrong route ownership,
            invalid time, or an unknown route status.
        DomainValidationError: If route or package topology is invalid.
        EntityNotFoundError: If a route segment has no map distance.
        RuntimeError: If an active schedule position lacks required fields.
    """
    if not route_rows:
        raise ValueError("Cannot map an active route without route rows.")

    generated_at = _require_naive_datetime(generated_at, "generated_at")
    typed_route_rows = [_as_active_route_row(row) for row in route_rows]
    typed_route_row = typed_route_rows[0]
    if any(row != typed_route_row for row in typed_route_rows[1:]):
        raise ValueError(f"Active route {typed_route_row['route_id']} has inconsistent route metadata.")

    if (typed_route_row["truck_vehicle_id"] is None) != (typed_route_row["truck_capacity"] is None):
        raise ValueError(f"Active route {typed_route_row['route_id']} has inconsistent truck metadata.")

    typed_stop_rows = sorted(
        (_as_active_route_stop_row(row) for row in route_rows),
        key=lambda stop: stop["stop_order"],
    )

    stop_orders = [stop["stop_order"] for stop in typed_stop_rows]
    if stop_orders != list(range(len(typed_stop_rows))):
        raise ValueError(f"Route {typed_route_row['route_id']} stop orders must be contiguous from zero.")

    path = RoutePath.create(*(stop["location_code"] for stop in typed_stop_rows))

    typed_package_rows = [_as_active_route_package_row(row) for row in package_rows]
    for package in typed_package_rows:
        if package["route_id"] != typed_route_row["route_id"]:
            raise ValueError(
                f"Package {package['package_id']} belongs to route "
                f"{package['route_id']}, not route {typed_route_row['route_id']}."
            )

    package_ids = [package["package_id"] for package in typed_package_rows]
    if len(package_ids) != len(set(package_ids)):
        raise ValueError(f"Active route {typed_route_row['route_id']} contains duplicate package rows.")

    invalid_package = next(
        (
            package
            for package in typed_package_rows
            if not path.includes_in_order(
                package["start_location"],
                package["end_location"],
            )
        ),
        None,
    )
    if invalid_package is not None:
        raise ValueError(
            f"Package {invalid_package['package_id']} does not follow active route "
            f"{typed_route_row['route_id']} in pickup-to-delivery order."
        )

    package_loads = tuple(
        PackageLoad(
            start_location=LocationCode(entry["start_location"]),
            end_location=LocationCode(entry["end_location"]),
            weight=float(entry["weight"]),
        )
        for entry in typed_package_rows
    )

    schedule = RouteScheduler.build(
        locations=path.locations,
        departure_time=typed_route_row["departure_time"],
    )

    converted_position = _map_active_position(schedule.position_at(generated_at))
    if converted_position is None:
        return None

    converted_status = RouteStatus(typed_route_row["status"])

    truck = (
        AssignedTruckOverview(
            truck_id=typed_route_row["truck_vehicle_id"],
            capacity=typed_route_row["truck_capacity"],
        )
        if typed_route_row["truck_vehicle_id"] is not None
        and typed_route_row["truck_capacity"] is not None
        else None
    )

    maximum_segment_load = RouteLoadCalculator.maximum_segment_load(
        locations=path.locations,
        packages=package_loads,
    )

    return ActiveRouteOverview(
        route_id=typed_route_row["route_id"],
        status=converted_status,
        start_location=path.start,
        end_location=path.end,
        position=converted_position,
        assigned_package_count=len(package_loads),
        truck=truck,
        maximum_segment_load=maximum_segment_load,
    )


def _map_active_position(position: RoutePosition) -> ActiveRoutePosition | None:
    """Map an active domain position to its overview projection.

    Args:
        position: Schedule-derived route position.

    Returns:
        Active position projection, or ``None`` when the position is inactive.

    Raises:
        RuntimeError: If an active position lacks fields required by its kind.
    """
    match position.kind:
        case RoutePositionKind.AT_STOP:
            if position.stop_city is None:
                raise RuntimeError("At-stop route position is missing its stop location.")

            return AtStopPosition(
                stop_location=position.stop_city,
                next_eta=position.next_eta,
            )

        case RoutePositionKind.IN_TRANSIT:
            if position.from_city is None or position.to_city is None or position.next_eta is None:
                raise RuntimeError("In-transit route position is missing segment information.")

            return InTransitPosition(
                from_location=position.from_city,
                to_location=position.to_city,
                next_eta=position.next_eta,
            )

        case _:
            return None


def _as_active_route_row(row: RowDict) -> ActiveRouteRow:
    """Validate route and optional truck metadata from an active-route row."""
    route_id = require_positive_int(row["route_id"], "route_id")
    departure_time = _require_naive_datetime(row["departure_time"], "departure_time")
    status = require_str(row["status"], "status")
    truck_vehicle_id = require_optional_positive_int(row["truck_vehicle_id"], "truck_vehicle_id")
    truck_capacity = require_optional_positive_int(row["truck_capacity"], "truck_capacity")

    return ActiveRouteRow(
        route_id=route_id,
        departure_time=departure_time,
        status=status,
        truck_vehicle_id=truck_vehicle_id,
        truck_capacity=truck_capacity,
    )


def _as_active_route_stop_row(row: RowDict) -> ActiveRouteStopRow:
    """Validate stop metadata from an active-route row."""
    stop_order = require_non_negative_int(row["stop_order"], "stop_order")
    location_code = require_str(row["location_code"], "location_code")

    return ActiveRouteStopRow(stop_order=stop_order, location_code=location_code)


def _as_active_route_package_row(row: RowDict) -> ActiveRoutePackageRow:
    """Validate and narrow one active-route package load row."""
    route_id = require_positive_int(row["route_id"], "route_id")
    package_id = require_positive_int(row["package_id"], "package_id")
    start_location = require_str(row["start_location"], "start_location")
    end_location = require_str(row["end_location"], "end_location")
    weight = require_finite_positive_decimal(row["weight"], "weight")

    return ActiveRoutePackageRow(
        route_id=route_id,
        package_id=package_id,
        start_location=start_location,
        end_location=end_location,
        weight=weight,
    )


def _parse_naive_datetime(value: str, field_name: str) -> datetime:
    """Parse an ISO 8601 string as timezone-naive app-local business time.

    Args:
        value: ISO 8601 datetime text.
        field_name: Field name used in validation errors.

    Returns:
        Parsed timezone-naive datetime.

    Raises:
        ValueError: If parsing fails or the timestamp is timezone-aware.
    """
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO 8601 datetime.") from exc

    return _require_naive_datetime(parsed, field_name)


def _require_naive_datetime(value: object, field_name: str) -> datetime:
    """Require a timezone-naive datetime used by app-local business time.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in validation errors.

    Returns:
        Validated timezone-naive datetime.

    Raises:
        TypeError: If ``value`` is not a datetime.
        ValueError: If ``value`` is timezone-aware.
    """
    parsed = require_datetime(value, field_name)
    if parsed.tzinfo is not None and parsed.utcoffset() is not None:
        raise ValueError(f"{field_name} must be timezone-naive.")

    return parsed
