"""In-memory fleet-overview query projection."""

from datetime import datetime
from heapq import nsmallest

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
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.route_schedule import RoutePosition, RoutePositionKind
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.truck_repository import TruckRepositoryPort
from src.shared.validation import require_naive_datetime, require_positive_int


class InMemoryFleetOverviewQuery:
    """Calculate fleet metrics from one snapshot of the memory repositories."""

    def __init__(
        self,
        package_repository: PackageRepositoryPort,
        route_repository: RouteRepositoryPort,
        truck_repository: TruckRepositoryPort,
    ) -> None:
        """Initialize the query with repositories that own current runtime state.

        Args:
            package_repository: Source of current package entities.
            route_repository: Source of current route aggregates.
            truck_repository: Source of current fleet trucks.
        """
        self._package_repository = package_repository
        self._route_repository = route_repository
        self._truck_repository = truck_repository

    def get_overview(
        self,
        *,
        generated_at: datetime,
        active_route_limit: int,
    ) -> FleetOverview:
        """Return fleet counts and active routes at ``generated_at``.

        Package, route, and truck collections are each loaded once. All
        derivative counts for an entity family are calculated from that same
        collection, preventing internally inconsistent metrics. Active routes
        are ordered by known next ETA, then route id; routes without a next ETA
        follow routes with known ETAs and are ordered by route id.

        Args:
            generated_at: App-local business time used for deadline and route
                position calculations.
            active_route_limit: Maximum active routes to return, from 1 to 100.

        Returns:
            Point-in-time fleet overview projection.

        Raises:
            TypeError: If ``generated_at`` is not a datetime or
                ``active_route_limit`` is not an integer.
            ValueError: If ``generated_at`` is timezone-aware,
                ``active_route_limit`` is outside 1 through 100, or mapped
                projection data violates its result contract.
            RuntimeError: If an active domain position lacks fields required
                by its kind.
        """
        generated_at = require_naive_datetime(generated_at, "generated_at")
        active_route_limit = require_positive_int(active_route_limit, "active_route_limit")
        if active_route_limit > 100:
            raise ValueError("active_route_limit must be less than or equal to 100.")

        packages = self._summarize_packages(self._package_repository.list_all(), generated_at)
        routes, active_routes = self._summarize_routes(
            self._route_repository.list_all(),
            generated_at,
        )
        trucks = self._summarize_trucks(self._truck_repository.list_fleet())

        return FleetOverview(
            generated_at=generated_at,
            packages=packages,
            routes=routes,
            trucks=trucks,
            active_routes=tuple(
                nsmallest(
                    active_route_limit,
                    active_routes,
                    key=lambda route: (
                        route.position.next_eta is None,
                        route.position.next_eta or generated_at,
                        route.route_id,
                    ),
                )
            ),
        )

    @staticmethod
    def _summarize_packages(
        packages: list[DeliveryPackage],
        generated_at: datetime,
    ) -> PackageOverview:
        """Calculate package metrics in one traversal of a repository snapshot.

        Args:
            packages: Package entities from one repository read.
            generated_at: Business time used to classify past-due packages.

        Returns:
            Package status, assignment, and deadline counts.
        """
        todo = 0
        in_progress = 0
        done = 0
        unassigned = 0
        past_due = 0

        for package in packages:
            match package.status:
                case ItemStatus.TODO:
                    todo += 1
                case ItemStatus.IN_PROGRESS:
                    in_progress += 1
                case ItemStatus.DONE:
                    done += 1

            if package.route_id is None:
                unassigned += 1

            if (
                package.status is not ItemStatus.DONE
                and package.expected_arrival is not None
                and package.expected_arrival < generated_at
            ):
                past_due += 1

        return PackageOverview(
            by_status=PackageStatusCounts(
                todo=todo,
                in_progress=in_progress,
                done=done,
            ),
            unassigned=unassigned,
            past_due=past_due,
        )

    @staticmethod
    def _summarize_routes(
        routes: list[DeliveryRoute],
        generated_at: datetime,
    ) -> tuple[RouteOverview, list[ActiveRouteOverview]]:
        """Calculate route metrics and active projections in one traversal.

        Completed routes contribute to lifecycle counts but are not evaluated
        for active temporal positions. Other routes are considered active only
        when their schedule-derived position is at a stop or in transit.

        Args:
            routes: Hydrated route aggregates from one repository read.
            generated_at: Business time used for deadlines and positions.

        Returns:
            Route metrics and unsorted active-route projections.

        Raises:
            RuntimeError: If an active route position lacks required fields.
            ValueError: If mapped projection data violates its result contract.
        """
        planned = 0
        scheduled = 0
        in_progress = 0
        completed = 0
        past_due = 0
        active_routes: list[ActiveRouteOverview] = []

        for route in routes:
            match route.status:
                case RouteStatus.PLANNED:
                    planned += 1
                case RouteStatus.SCHEDULED:
                    scheduled += 1
                case RouteStatus.IN_PROGRESS:
                    in_progress += 1
                case RouteStatus.COMPLETED:
                    completed += 1

            if route.status is RouteStatus.COMPLETED:
                continue

            if route.eta_final is not None and route.eta_final < generated_at:
                past_due += 1

            position = route.current_position(generated_at)
            if position.kind not in {
                RoutePositionKind.AT_STOP,
                RoutePositionKind.IN_TRANSIT,
            }:
                continue

            active_routes.append(InMemoryFleetOverviewQuery._map_active_route(route, position))

        return (
            RouteOverview(
                by_status=RouteStatusCounts(
                    planned=planned,
                    scheduled=scheduled,
                    in_progress=in_progress,
                    completed=completed,
                ),
                past_due=past_due,
            ),
            active_routes,
        )

    @staticmethod
    def _summarize_trucks(trucks: list[Truck]) -> TruckOverview:
        """Calculate truck status and location metrics in one traversal.

        Args:
            trucks: Fleet trucks from one repository read.

        Returns:
            Truck status counts and unknown-location count.
        """
        free = 0
        on_the_way = 0
        unknown_location = 0

        for truck in trucks:
            match truck.status:
                case TruckStatus.FREE:
                    free += 1
                case TruckStatus.ON_THE_WAY:
                    on_the_way += 1

            if truck.current_location is None:
                unknown_location += 1

        return TruckOverview(
            by_status=TruckStatusCounts(
                free=free,
                on_the_way=on_the_way,
            ),
            unknown_location=unknown_location,
        )

    @staticmethod
    def _map_active_position(position: RoutePosition) -> ActiveRoutePosition:
        """Narrow an active domain position to its overview representation.

        Args:
            position: Domain route position classified as at-stop or in-transit.

        Returns:
            Discriminated active-route position projection.

        Raises:
            RuntimeError: If fields required by the position kind are missing.
            ValueError: If the supplied position kind is not active.
        """
        match position.kind:
            case RoutePositionKind.IN_TRANSIT:
                if position.from_city is None or position.to_city is None or position.next_eta is None:
                    raise RuntimeError("In-transit route position is missing segment information.")

                return InTransitPosition(
                    from_location=position.from_city,
                    to_location=position.to_city,
                    next_eta=position.next_eta,
                )

            case RoutePositionKind.AT_STOP:
                if position.stop_city is None:
                    raise RuntimeError("At-stop route position is missing its stop location.")

                return AtStopPosition(
                    stop_location=position.stop_city,
                    next_eta=position.next_eta,
                )

            case _:
                raise ValueError(f"Cannot map inactive route position: {position.kind.value}")

    @staticmethod
    def _map_active_route(route: DeliveryRoute, position: RoutePosition) -> ActiveRouteOverview:
        """Map an active route aggregate and calculated position to a projection.

        Args:
            route: Hydrated route aggregate considered active at query time.
            position: Position calculated for the query's generation time.

        Returns:
            Active-route overview including assignment and segment-load data.

        Raises:
            RuntimeError: If the active position is structurally incomplete.
            ValueError: If projection values violate result-model invariants.
        """
        return ActiveRouteOverview(
            route_id=route.route_id,
            status=route.status,
            start_location=route.start_location,
            end_location=route.end_location,
            position=InMemoryFleetOverviewQuery._map_active_position(position),
            assigned_package_count=len(route.packages),
            truck=AssignedTruckOverview(
                truck_id=route.truck.vehicle_id,
                capacity=route.truck.capacity,
            )
            if route.truck is not None
            else None,
            maximum_segment_load=route.maximum_segment_load(),
        )
