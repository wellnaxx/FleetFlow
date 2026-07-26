"""HTTP response schemas for point-in-time fleet overview projections."""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    Field,
    FiniteFloat,
    NonNegativeInt,
    PositiveInt,
    computed_field,
)

from src.application.results.fleet_overview import (
    ActiveRouteOverview,
    ActiveRoutePosition,
    AssignedTruckOverview,
    AtStopPosition,
    FleetOverview,
    InTransitPosition,
    PackageOverview,
    PackageStatusCounts,
    RouteOverview,
    RouteStatusCounts,
    TruckOverview,
    TruckStatusCounts,
)
from src.domain.enums.route_status import RouteStatus

type LocationCodeText = Annotated[
    str,
    Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="Three-letter uppercase fleet location code.",
    ),
]
type NonNegativeFiniteFloat = Annotated[FiniteFloat, Field(ge=0)]


class PackageStatusCountsResponse(BaseModel):
    """Package counts grouped by lifecycle status."""

    todo: NonNegativeInt = Field(
        description="Packages waiting to be picked up.",
    )
    in_progress: NonNegativeInt = Field(
        description="Packages currently in transit.",
    )
    done: NonNegativeInt = Field(
        description="Packages that have been delivered.",
    )

    @computed_field(description="Total number of packages across all lifecycle statuses.")
    @property
    def total(self) -> NonNegativeInt:
        """Return the total package population across all statuses."""
        return self.todo + self.in_progress + self.done

    @classmethod
    def from_counts(cls, counts: PackageStatusCounts) -> Self:
        """Build an HTTP response from application package status counts.

        Args:
            counts: Validated package status projection.

        Returns:
            Serialized package status counts.
        """
        return cls(
            todo=counts.todo,
            in_progress=counts.in_progress,
            done=counts.done,
        )


class PackageOverviewResponse(BaseModel):
    """Package lifecycle, assignment, and deadline summary."""

    by_status: PackageStatusCountsResponse = Field(
        description="Exhaustive package counts grouped by lifecycle status.",
    )
    unassigned: NonNegativeInt = Field(
        description="Packages that are not assigned to a route.",
    )
    past_due: NonNegativeInt = Field(
        description="Undelivered packages whose expected arrival has passed.",
    )

    @classmethod
    def from_overview(cls, overview: PackageOverview) -> Self:
        """Build an HTTP response from an application package overview.

        Args:
            overview: Validated package overview projection.

        Returns:
            Serialized package overview.
        """
        return cls(
            by_status=PackageStatusCountsResponse.from_counts(overview.by_status),
            unassigned=overview.unassigned,
            past_due=overview.past_due,
        )


class RouteStatusCountsResponse(BaseModel):
    """Route counts grouped by lifecycle status."""

    planned: NonNegativeInt = Field(
        description="Routes that have not been scheduled.",
    )
    scheduled: NonNegativeInt = Field(
        description="Scheduled routes that have not started.",
    )
    in_progress: NonNegativeInt = Field(
        description="Routes currently underway.",
    )
    completed: NonNegativeInt = Field(
        description="Routes that have completed their schedules.",
    )

    @computed_field(description="Total number of routes across all lifecycle statuses.")
    @property
    def total(self) -> NonNegativeInt:
        """Return the total route population across all statuses."""
        return self.planned + self.scheduled + self.in_progress + self.completed

    @classmethod
    def from_counts(cls, counts: RouteStatusCounts) -> Self:
        """Build an HTTP response from application route status counts.

        Args:
            counts: Validated route status projection.

        Returns:
            Serialized route status counts.
        """
        return cls(
            planned=counts.planned,
            scheduled=counts.scheduled,
            in_progress=counts.in_progress,
            completed=counts.completed,
        )


class RouteOverviewResponse(BaseModel):
    """Route lifecycle and overdue-work summary."""

    by_status: RouteStatusCountsResponse = Field(
        description="Exhaustive route counts grouped by lifecycle status.",
    )
    past_due: NonNegativeInt = Field(
        description="Non-completed routes whose final estimated arrival has passed.",
    )

    @classmethod
    def from_overview(cls, overview: RouteOverview) -> Self:
        """Build an HTTP response from an application route overview.

        Args:
            overview: Validated route overview projection.

        Returns:
            Serialized route overview.
        """
        return cls(
            by_status=RouteStatusCountsResponse.from_counts(overview.by_status),
            past_due=overview.past_due,
        )


class TruckStatusCountsResponse(BaseModel):
    """Truck counts grouped by assignment status."""

    free: NonNegativeInt = Field(
        description="Trucks currently available for assignment.",
    )
    on_the_way: NonNegativeInt = Field(
        description="Trucks currently assigned to routes.",
    )

    @computed_field(description="Total number of trucks across all assignment statuses.")
    @property
    def total(self) -> NonNegativeInt:
        """Return the total truck population across all statuses."""
        return self.free + self.on_the_way

    @classmethod
    def from_counts(cls, counts: TruckStatusCounts) -> Self:
        """Build an HTTP response from application truck status counts.

        Args:
            counts: Validated truck status projection.

        Returns:
            Serialized truck status counts.
        """
        return cls(
            free=counts.free,
            on_the_way=counts.on_the_way,
        )


class TruckOverviewResponse(BaseModel):
    """Truck assignment and location-availability summary."""

    by_status: TruckStatusCountsResponse = Field(
        description="Exhaustive truck counts grouped by assignment status.",
    )
    unknown_location: NonNegativeInt = Field(
        description="Trucks whose current location is unavailable.",
    )

    @classmethod
    def from_overview(cls, overview: TruckOverview) -> Self:
        """Build an HTTP response from an application truck overview.

        Args:
            overview: Validated truck overview projection.

        Returns:
            Serialized truck overview.
        """
        return cls(
            by_status=TruckStatusCountsResponse.from_counts(overview.by_status),
            unknown_location=overview.unknown_location,
        )


class InTransitPositionResponse(BaseModel):
    """Active-route position while travelling between adjacent stops."""

    from_location: LocationCodeText = Field(
        description="Location from which the active route is travelling.",
    )
    to_location: LocationCodeText = Field(
        description="Next location toward which the active route is travelling.",
    )
    next_eta: datetime = Field(
        description="Scheduled arrival time at the next location.",
    )
    kind: Literal["in_transit"] = Field(
        default="in_transit",
        description="Discriminator identifying an in-transit route position.",
    )


class AtStopPositionResponse(BaseModel):
    """Active-route position at a scheduled stop."""

    stop_location: LocationCodeText = Field(
        description="Scheduled location at which the route is currently stopped.",
    )
    next_eta: datetime | None = Field(
        description="Scheduled arrival at the following stop, or null at the final stop.",
    )
    kind: Literal["at_stop"] = Field(
        default="at_stop",
        description="Discriminator identifying an at-stop route position.",
    )


type ActiveRoutePositionResponse = Annotated[
    InTransitPositionResponse | AtStopPositionResponse,
    Field(discriminator="kind"),
]


class AssignedTruckOverviewResponse(BaseModel):
    """Assigned truck identity and capacity exposed for an active route."""

    truck_id: PositiveInt = Field(
        description="Stable identifier of the truck assigned to the route.",
    )
    capacity: PositiveInt = Field(
        description="Maximum truck cargo capacity in kilograms.",
    )

    @classmethod
    def from_truck(cls, truck: AssignedTruckOverview) -> Self:
        """Build an HTTP response from assigned-truck overview data.

        Args:
            truck: Validated assigned-truck projection.

        Returns:
            Serialized assigned-truck details.
        """
        return cls(
            truck_id=truck.truck_id,
            capacity=truck.capacity,
        )


class ActiveRouteOverviewResponse(BaseModel):
    """Operational details for one route active at overview generation time."""

    route_id: PositiveInt = Field(
        description="Stable identifier of the active route.",
    )
    status: RouteStatus = Field(
        description="Persisted lifecycle status of the active route.",
    )
    start_location: LocationCodeText = Field(
        description="First location in the route path.",
    )
    end_location: LocationCodeText = Field(
        description="Final location in the route path.",
    )
    position: ActiveRoutePositionResponse = Field(
        description="Schedule-derived position at overview generation time.",
    )
    assigned_package_count: NonNegativeInt = Field(
        description="Number of packages assigned to the route.",
    )
    truck: AssignedTruckOverviewResponse | None = Field(
        description="Assigned truck details, or null when no truck is assigned.",
    )
    maximum_segment_load: NonNegativeFiniteFloat = Field(
        description="Maximum simultaneous package load on any route segment, in kilograms.",
    )
    capacity_utilization_percent: NonNegativeFiniteFloat | None = Field(
        description=(
            "Maximum segment load as a percentage of assigned truck capacity; "
            "null without a truck and potentially greater than 100 for an overloaded route."
        ),
    )

    @classmethod
    def from_route(cls, route: ActiveRouteOverview) -> Self:
        """Build an HTTP response from one active-route projection.

        Location value objects are converted to JSON strings. Capacity
        utilization is copied from the application result so the HTTP layer
        does not duplicate application calculation rules.

        Args:
            route: Validated active-route overview projection.

        Returns:
            Serialized active-route details.
        """
        return cls(
            route_id=route.route_id,
            status=route.status,
            start_location=str(route.start_location),
            end_location=str(route.end_location),
            position=_map_active_route_position(route.position),
            assigned_package_count=route.assigned_package_count,
            truck=(AssignedTruckOverviewResponse.from_truck(route.truck) if route.truck is not None else None),
            maximum_segment_load=route.maximum_segment_load,
            capacity_utilization_percent=route.capacity_utilization_percent,
        )


class FleetOverviewResponse(BaseModel):
    """Complete fleet overview returned by the HTTP API."""

    generated_at: datetime = Field(
        description="App-local business time at which the overview was calculated.",
    )
    packages: PackageOverviewResponse = Field(
        description="Package lifecycle and operational summary.",
    )
    routes: RouteOverviewResponse = Field(
        description="Route lifecycle and overdue-work summary.",
    )
    trucks: TruckOverviewResponse = Field(
        description="Truck assignment and location-availability summary.",
    )
    active_routes: list[ActiveRouteOverviewResponse] = Field(
        description="Ordered active-route details selected for the overview.",
    )

    @classmethod
    def from_overview(cls, overview: FleetOverview) -> Self:
        """Build an HTTP response from the application fleet overview.

        Args:
            overview: Point-in-time fleet projection returned by the use case.

        Returns:
            Fully serialized fleet overview response.
        """
        return cls(
            generated_at=overview.generated_at,
            packages=PackageOverviewResponse.from_overview(overview.packages),
            routes=RouteOverviewResponse.from_overview(overview.routes),
            trucks=TruckOverviewResponse.from_overview(overview.trucks),
            active_routes=[ActiveRouteOverviewResponse.from_route(route) for route in overview.active_routes],
        )


def _map_active_route_position(
    position: ActiveRoutePosition,
) -> ActiveRoutePositionResponse:
    """Convert an application route position into its HTTP union member.

    Args:
        position: Validated at-stop or in-transit application projection.

    Returns:
        Discriminated HTTP position response with string location codes.
    """
    match position:
        case AtStopPosition(stop_location=stop_location, next_eta=next_eta):
            return AtStopPositionResponse(
                stop_location=str(stop_location),
                next_eta=next_eta,
            )
        case InTransitPosition(
            from_location=from_location,
            to_location=to_location,
            next_eta=next_eta,
        ):
            return InTransitPositionResponse(
                from_location=str(from_location),
                to_location=str(to_location),
                next_eta=next_eta,
            )
