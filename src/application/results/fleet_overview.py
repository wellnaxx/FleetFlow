"""Read-only application projections for the fleet operations overview."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.domain.enums.route_status import RouteStatus
from src.domain.value_objects.location_code import LocationCode
from src.shared.validation import (
    require_naive_datetime,
    require_non_negative_finite_float,
    require_non_negative_int,
    require_positive_int,
)


@dataclass(frozen=True, slots=True)
class PackageStatusCounts:
    """Exhaustive package counts grouped by lifecycle status.

    Attributes:
        todo: Packages waiting for pickup.
        in_progress: Packages currently in transit.
        done: Packages that have been delivered.
    """

    todo: int
    in_progress: int
    done: int

    def __post_init__(self) -> None:
        """Require non-negative package status counts."""
        require_non_negative_int(self.todo, "todo")
        require_non_negative_int(self.in_progress, "in_progress")
        require_non_negative_int(self.done, "done")

    @property
    def total(self) -> int:
        """Return the total number of packages across all statuses."""
        return self.todo + self.in_progress + self.done


@dataclass(frozen=True, slots=True)
class PackageOverview:
    """Package status and cross-cutting operational counts.

    ``unassigned`` and ``past_due`` overlap with ``by_status`` categories and
    therefore must not be added to ``by_status.total``.

    Attributes:
        by_status: Exhaustive package lifecycle counts.
        unassigned: Packages that are not assigned to a route.
        past_due: Undelivered packages whose expected arrival is earlier than
            the overview generation time.
    """

    by_status: PackageStatusCounts
    unassigned: int
    past_due: int

    def __post_init__(self) -> None:
        """Validate package operational counts against the status snapshot.

        Raises:
            TypeError: If an operational count is not an integer or is a boolean.
            ValueError: If a count is negative or exceeds its applicable
                package population.
        """
        require_non_negative_int(self.unassigned, "unassigned")
        require_non_negative_int(self.past_due, "past_due")

        if self.unassigned > self.by_status.total:
            raise ValueError("unassigned cannot exceed the total package count.")

        undelivered = self.by_status.todo + self.by_status.in_progress
        if self.past_due > undelivered:
            raise ValueError("past_due cannot exceed the undelivered package count.")


@dataclass(frozen=True, slots=True)
class RouteStatusCounts:
    """Exhaustive route counts grouped by lifecycle status.

    Attributes:
        planned: Unscheduled routes.
        scheduled: Scheduled routes that have not started.
        in_progress: Routes currently underway.
        completed: Routes that have completed their schedules.
    """

    planned: int
    scheduled: int
    in_progress: int
    completed: int

    def __post_init__(self) -> None:
        """Require non-negative route status counts."""
        require_non_negative_int(self.planned, "planned")
        require_non_negative_int(self.scheduled, "scheduled")
        require_non_negative_int(self.in_progress, "in_progress")
        require_non_negative_int(self.completed, "completed")

    @property
    def total(self) -> int:
        """Return the total number of routes across all statuses."""
        return self.planned + self.scheduled + self.in_progress + self.completed


@dataclass(frozen=True, slots=True)
class RouteOverview:
    """Route status and cross-cutting operational counts.

    ``past_due`` overlaps with the non-completed status categories and is not
    part of ``by_status.total``.

    Attributes:
        by_status: Exhaustive route lifecycle counts.
        past_due: Non-completed routes whose final ETA is earlier than the
            overview generation time.
    """

    by_status: RouteStatusCounts
    past_due: int

    def __post_init__(self) -> None:
        """Validate past-due routes against the non-completed population.

        Raises:
            TypeError: If ``past_due`` is not an integer or is a boolean.
            ValueError: If ``past_due`` is negative or exceeds the number of
                non-completed routes.
        """
        require_non_negative_int(self.past_due, "past_due")

        non_completed = self.by_status.planned + self.by_status.scheduled + self.by_status.in_progress
        if self.past_due > non_completed:
            raise ValueError("past_due cannot exceed the non-completed route count.")


@dataclass(frozen=True, slots=True)
class TruckStatusCounts:
    """Exhaustive truck counts grouped by assignment status.

    Attributes:
        free: Trucks available for assignment.
        on_the_way: Trucks currently assigned to routes.
    """

    free: int
    on_the_way: int

    def __post_init__(self) -> None:
        """Require non-negative truck status counts."""
        require_non_negative_int(self.free, "free")
        require_non_negative_int(self.on_the_way, "on_the_way")

    @property
    def total(self) -> int:
        """Return the total number of trucks across all statuses."""
        return self.free + self.on_the_way


@dataclass(frozen=True, slots=True)
class TruckOverview:
    """Truck status and location-availability counts.

    ``unknown_location`` overlaps with ``by_status`` and therefore must not be
    added to ``by_status.total``.

    Attributes:
        by_status: Exhaustive truck assignment-status counts.
        unknown_location: Trucks whose current location is unavailable.
    """

    by_status: TruckStatusCounts
    unknown_location: int

    def __post_init__(self) -> None:
        """Validate unknown locations against the total truck population.

        Raises:
            TypeError: If ``unknown_location`` is not an integer or is a boolean.
            ValueError: If ``unknown_location`` is negative or exceeds the
                total number of trucks.
        """
        require_non_negative_int(self.unknown_location, "unknown_location")
        if self.unknown_location > self.by_status.total:
            raise ValueError("unknown_location cannot exceed the total truck count.")


@dataclass(frozen=True, slots=True)
class AssignedTruckOverview:
    """Truck capacity details attached to an active-route projection.

    Attributes:
        truck_id: Stable fleet truck identifier.
        capacity: Maximum truck cargo capacity in kilograms.
    """

    truck_id: int
    capacity: int

    def __post_init__(self) -> None:
        """Require a positive capacity for utilization calculations.

        Raises:
            TypeError: If ``capacity`` is not an integer or is a boolean.
            ValueError: If ``capacity`` is zero or negative.
        """
        require_positive_int(self.capacity, "capacity")


@dataclass(frozen=True, slots=True)
class InTransitPosition:
    """Position of a route currently travelling between adjacent stops.

    Attributes:
        from_location: Segment origin.
        to_location: Segment destination.
        next_eta: Scheduled arrival at the segment destination.
        kind: Stable discriminator used by driving adapters.
    """

    from_location: LocationCode
    to_location: LocationCode
    next_eta: datetime
    kind: Literal["in_transit"] = "in_transit"


@dataclass(frozen=True, slots=True)
class AtStopPosition:
    """Position of a route currently at a scheduled stop.

    Attributes:
        stop_location: Current route stop.
        next_eta: Scheduled arrival at the following stop, or ``None`` at the
            final stop.
        kind: Stable discriminator used by driving adapters.
    """

    stop_location: LocationCode
    next_eta: datetime | None
    kind: Literal["at_stop"] = "at_stop"


type ActiveRoutePosition = InTransitPosition | AtStopPosition


@dataclass(frozen=True, slots=True)
class ActiveRouteOverview:
    """Operational projection of one route active at overview generation time.

    The persisted lifecycle ``status`` is retained separately from the
    schedule-derived ``position`` so consumers can observe temporarily stale
    state when reconciliation has not yet run.

    Attributes:
        route_id: Stable route identifier.
        status: Persisted route lifecycle status.
        start_location: First route stop.
        end_location: Final route stop.
        position: Schedule-derived current stop or segment.
        assigned_package_count: Number of packages assigned to the route.
        truck: Assigned truck capacity details, or ``None``.
        maximum_segment_load: Maximum simultaneous package weight carried on
            any route segment, in kilograms.
    """

    route_id: int
    status: RouteStatus
    start_location: LocationCode
    end_location: LocationCode
    position: ActiveRoutePosition
    assigned_package_count: int
    truck: AssignedTruckOverview | None
    maximum_segment_load: float

    def __post_init__(self) -> None:
        """Validate active-route aggregate counts and load values.

        Raises:
            TypeError: If the package count or segment load has an invalid
                numeric type.
            ValueError: If either aggregate is negative or the segment load is
                non-finite.
        """
        require_non_negative_int(self.assigned_package_count, "assigned_package_count")
        object.__setattr__(
            self,
            "maximum_segment_load",
            require_non_negative_finite_float(self.maximum_segment_load, "maximum_segment_load"),
        )

    @property
    def capacity_utilization_percent(self) -> float | None:
        """Return maximum segment-load utilization, or ``None`` without a truck.

        The raw percentage is intentionally not rounded. Driving adapters own
        presentation-specific rounding.
        """
        if self.truck is None:
            return None
        return (self.maximum_segment_load / self.truck.capacity) * 100


@dataclass(frozen=True, slots=True)
class FleetOverview:
    """Point-in-time operational summary of the current fleet.

    Attributes:
        generated_at: App-local business time used for temporal calculations.
        packages: Package lifecycle and operational counts.
        routes: Route lifecycle and operational counts.
        trucks: Truck status and location counts.
        active_routes: Active route projections ordered by the query adapter.
    """

    generated_at: datetime
    packages: PackageOverview
    routes: RouteOverview
    trucks: TruckOverview
    active_routes: tuple[ActiveRouteOverview, ...]

    def __post_init__(self) -> None:
        """Require the app-local timestamp used to build this projection."""
        require_naive_datetime(self.generated_at, "generated_at")
