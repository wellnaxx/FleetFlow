"""Delivery route aggregate, lifecycle transitions, and assignment rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise
from typing import TYPE_CHECKING

from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin
from src.domain.enums.route_status import RouteStatus
from src.domain.events.route_events import (
    PackageAssignedToRoute,
    PackageDetachedFromRoute,
    RouteCompleted,
    RouteCreated,
    RouteRemoved,
    RouteScheduled,
    RouteStarted,
    TruckAssignedToRoute,
    TruckReleasedFromRoute,
)
from src.domain.exceptions import DomainConflictError, DomainValidationError, EntityNotFoundError
from src.domain.services.map import Map
from src.domain.services.package_assignment_policy import PackageAssignmentPolicy
from src.domain.services.route_load_calculator import RouteLoadCalculator
from src.domain.services.route_scheduler import RouteScheduler
from src.domain.validation import require_positive_int
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.package_load import PackageLoad
from src.domain.value_objects.route_path import RoutePath
from src.domain.value_objects.route_schedule import RoutePosition, RoutePositionKind

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.truck import Truck
    from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
    from src.domain.enums.truck_release_reasons import TruckReleaseReason
    from src.domain.events.base import DomainEvent
    from src.domain.value_objects.route_schedule import RouteSchedule


@dataclass(frozen=True, slots=True)
class RouteStateSnapshot:
    """Captured mutable state for restoring a route after a failed operation."""

    departure_time: datetime | None
    status: RouteStatus
    truck: Truck | None
    packages: tuple[DeliveryPackage, ...]


class DeliveryRoute(DomainEventRecorderMixin):
    """Route aggregate for packages and an optional assigned truck."""

    SPEED_KMPH: int = RouteScheduler.DEFAULT_SPEED_KMPH

    def __init__(
        self,
        *locations: str | LocationCode,
        departure_time: datetime | None = None,
        route_id: int,
    ) -> None:
        """Create a delivery route.

        Args:
            *locations: Ordered raw or typed location codes from origin to destination.
            departure_time: Optional scheduled departure time.
            route_id: Stable route identifier.

        Raises:
            DomainValidationError: If ``route_id`` is not a positive integer,
                fewer than two locations are supplied, any location is
                unknown, or a location is repeated.
            EntityNotFoundError: If a departure time is supplied and no map distance exists
                between adjacent route locations.
        """
        self.route_id = require_positive_int(route_id, "route_id")
        self._path = RoutePath.create(*locations)
        self.truck: Truck | None = None
        self._packages: list[DeliveryPackage] = []
        self.status: RouteStatus = RouteStatus.SCHEDULED if departure_time is not None else RouteStatus.PLANNED

        self._schedule: RouteSchedule | None = (
            RouteScheduler.build(
                locations=self._path.locations,
                departure_time=departure_time,
                speed_kmph=self.SPEED_KMPH,
            )
            if departure_time is not None
            else None
        )

        self._pending_events: list[DomainEvent] = []

    @property
    def departure_time(self) -> datetime | None:
        """Scheduled departure time, or None while the route is planned."""
        return self._schedule.departure_time if self._schedule is not None else None

    @property
    def locations(self) -> list[LocationCode]:
        """Route locations in travel order."""
        return list(self._path.locations)

    @property
    def start_location(self) -> LocationCode:
        """First location on the route."""
        return self._path.start

    @property
    def end_location(self) -> LocationCode:
        """Final location on the route."""
        return self._path.end

    @property
    def packages(self) -> tuple[DeliveryPackage, ...]:
        """Assigned packages as an immutable snapshot of the internal collection."""
        return tuple(self._packages)

    @classmethod
    def create(
        cls,
        *locations: str | LocationCode,
        departure_time: datetime | None = None,
        route_id: int,
        occurred_at: datetime | None = None,
    ) -> DeliveryRoute:
        """Create a delivery route and record its creation event.

        Unlike direct construction, this factory records a `RouteCreated`
        domain event. Persistence mappers should use the constructor when
        rehydrating existing routes.

        Args:
            *locations: Ordered raw or typed location codes from origin to destination.
            departure_time: Optional scheduled departure time.
            route_id: Stable route identifier.
            occurred_at: Business time of creation. Defaults to the current time.

        Returns:
            Newly created route with one pending `RouteCreated` event.

        Raises:
            DomainValidationError: If ``route_id`` is not a positive integer,
                fewer than two locations are supplied, any location is
                unknown, or a location is repeated.
            EntityNotFoundError: If a departure time is supplied and no map distance exists
                between adjacent route locations.
        """
        route = cls(*locations, departure_time=departure_time, route_id=route_id)

        route._record_event(
            RouteCreated(
                route_id=route.route_id,
                locations=tuple(route.locations),
                departure_time=route.departure_time,
                initial_status=route.status,
                expected_completion_time=route.eta_final,
                occurred_at=occurred_at or datetime.now(),
            )
        )

        return route

    def mark_started(self, *, occurred_at: datetime) -> None:
        """Move a scheduled route into progress and record the transition.

        Args:
            occurred_at: Business time at which the route started.

        Raises:
            DomainConflictError: If the route is not currently scheduled.
        """
        if self.status is not RouteStatus.SCHEDULED:
            raise DomainConflictError(f"Route {self.route_id} cannot start from status {self.status.value}.")

        previous_status = self.status
        self.status = RouteStatus.IN_PROGRESS
        self._record_event(
            RouteStarted(
                route_id=self.route_id,
                previous_status=previous_status,
                new_status=self.status,
                occurred_at=occurred_at,
            )
        )

    def mark_completed(self, *, occurred_at: datetime) -> None:
        """Complete a scheduled or in-progress route and record the transition.

        Reconciliation may observe completion without first observing the
        in-progress state, so completion from `SCHEDULED` is valid.

        Args:
            occurred_at: Business time at which the route completed.

        Raises:
            DomainConflictError: If the route is neither scheduled nor in progress.
        """
        if self.status not in (RouteStatus.SCHEDULED, RouteStatus.IN_PROGRESS):
            raise DomainConflictError(f"Route {self.route_id} cannot complete from status {self.status.value}.")

        if not self.departure_time:
            raise DomainConflictError(f"Route {self.route_id} cannot complete without a departure time.")

        if not self.eta_final:
            raise DomainConflictError(
                f"Route {self.route_id} cannot complete without an expected completion time."
            )

        previous_status = self.status
        self.status = RouteStatus.COMPLETED
        self._record_event(
            RouteCompleted(
                route_id=self.route_id,
                previous_status=previous_status,
                new_status=self.status,
                departure_time=self.departure_time,
                expected_completion_time=self.eta_final,
                occurred_at=occurred_at,
            )
        )

    def record_removal(
        self, *, detached_package_ids: tuple[int, ...], released_truck_id: int | None, occurred_at: datetime
    ) -> None:
        """Record that this route was removed from the system.

        Args:
            detached_package_ids: Identifiers of packages detached during removal.
            released_truck_id: Identifier of the released truck, if one was assigned.
            occurred_at: Business time at which removal occurred.
        """
        self._record_event(
            RouteRemoved(
                route_id=self.route_id,
                previous_status=self.status,
                previous_locations=tuple(self.locations),
                previous_departure_time=self.departure_time,
                previous_expected_completion_time=self.eta_final,
                detached_package_ids=detached_package_ids,
                released_truck_id=released_truck_id,
                occurred_at=occurred_at,
            )
        )

    def snapshot_state(self) -> RouteStateSnapshot:
        """Capture mutable route state.

        Returns:
            Snapshot that can be passed to `restore_state`.
        """
        return RouteStateSnapshot(
            departure_time=self.departure_time,
            status=self.status,
            truck=self.truck,
            packages=tuple(self._packages),
        )

    def restore_state(self, snapshot: RouteStateSnapshot) -> None:
        """Restore mutable route state from a prior snapshot.

        Args:
            snapshot: State captured by `snapshot_state`.
        """
        restored_schedule = (
            RouteScheduler.build(
                locations=self._path.locations,
                departure_time=snapshot.departure_time,
                speed_kmph=self.SPEED_KMPH,
            )
            if snapshot.departure_time is not None
            else None
        )

        self._schedule = restored_schedule
        self.status = snapshot.status
        self.truck = snapshot.truck
        self._packages = list(snapshot.packages)

    @property
    def total_distance_km(self) -> int:
        """Total travel distance in kilometres."""
        return (
            self._schedule.total_distance_km
            if self._schedule is not None
            else int(sum(Map.get_distance(start, end) for start, end in pairwise(self._path.locations)))
        )

    @property
    def eta_final(self) -> datetime | None:
        """Expected arrival time at the final stop, if scheduled."""
        return self._schedule.eta_final if self._schedule is not None else None

    def schedule(self, departure_time: datetime, *, occurred_at: datetime) -> None:
        """Schedule the route, rebuild stop timing information, and record a `RouteScheduled` event.

        Args:
            departure_time: Departure time for the first route location.
            occurred_at: Business time at which the route is scheduled successfully.

        Raises:
            DomainConflictError: If route is already scheduled.
            DomainValidationError: If a valid schedule cannot be calculated.
            EntityNotFoundError: If no map distance exists between adjacent locations.
        """
        if self._schedule is not None:
            raise DomainConflictError(f"Route {self.route_id} is already scheduled.")

        previous_status = self.status
        previous_departure_time = self.departure_time
        previous_expected_completion_time = self.eta_final
        new_schedule = RouteScheduler.build(
            locations=self._path.locations,
            departure_time=departure_time,
            speed_kmph=self.SPEED_KMPH,
        )
        self._schedule = new_schedule
        self.status = RouteStatus.SCHEDULED

        expected_completion_time = new_schedule.eta_final

        self._record_event(
            RouteScheduled(
                route_id=self.route_id,
                previous_status=previous_status,
                new_status=self.status,
                previous_departure_time=previous_departure_time,
                new_departure_time=departure_time,
                previous_expected_completion_time=previous_expected_completion_time,
                new_expected_completion_time=expected_completion_time,
                occurred_at=occurred_at,
            )
        )

    def arrival_time_at(self, city: str | LocationCode) -> datetime:
        """Return the scheduled arrival time for a route city.

        Args:
            city: Raw or typed location code on this route.

        Returns:
            Scheduled arrival time at the requested city.

        Raises:
            DomainConflictError: If the route is unscheduled.
            DomainValidationError: If the city is not on the route path.
        """
        if self._schedule is None:
            raise DomainConflictError("Route not scheduled yet.")
        city = LocationCode(city)
        try:
            return self._schedule.arrival_time_at(city)
        except DomainValidationError:
            raise DomainValidationError(f"City {city} is not on route {self.route_id}.") from None

    def current_position(self, now: datetime | None = None) -> RoutePosition:
        """Return a snapshot of the route's current position.

        Args:
            now: Clock value used to evaluate route progress. Uses current time
                when omitted.

        Returns:
            Position descriptor for the route at the requested time.
        """
        if self._schedule is None:
            return RoutePosition(kind=RoutePositionKind.UNSCHEDULED, stop_city=self.start_location)

        return self._schedule.position_at(now or datetime.now())

    def includes_in_order(self, start: str | LocationCode, end: str | LocationCode) -> bool:
        """Return whether the route visits start before end.

        Args:
            start: Candidate raw or typed pickup location code.
            end: Candidate raw or typed delivery location code.

        Returns:
            True when both locations are present and start appears before end.
        """
        return self._path.includes_in_order(start, end)

    def can_accept_package(self, package: DeliveryPackage, now: datetime | None = None) -> str | None:
        """Validate whether a package can be assigned to this route.

        Args:
            package: Package being evaluated.
            now: Clock value used for live pickup-pass validation.

        Returns:
            None when the package is acceptable, otherwise a human-readable
            rejection reason.
        """
        decision = PackageAssignmentPolicy.evaluate(route=self, package=package, now=now)
        return decision.message

    def assign_package(
        self, package: DeliveryPackage, now: datetime | None = None, *, occurred_at: datetime
    ) -> None:
        """Assign a package after validating route compatibility.

        Args:
            package: Package to assign.
            now: Clock value used for live pickup-pass validation.
            occurred_at: Business time at which the assignment succeeded.

        Raises:
            DomainConflictError: If the package is incompatible with the route.
        """
        if self._has_package(package):
            return

        if error := self.can_accept_package(package, now=now):
            raise DomainConflictError(error)

        self._packages.append(package)
        previous_route_id = package.route.route_id if package.route is not None else None
        previous_expected_arrival = package.expected_arrival
        package.route = self
        self._update_expected_arrival(package)

        self._record_event(
            PackageAssignedToRoute(
                package_id=package.package_id,
                previous_route_id=previous_route_id,
                new_route_id=self.route_id,
                previous_expected_arrival=previous_expected_arrival,
                new_expected_arrival=package.expected_arrival,
                occurred_at=occurred_at,
            )
        )

    def detach_package(
        self, package: DeliveryPackage, *, reason: PackageDetachmentReason, occurred_at: datetime
    ) -> None:
        """Detach a package and clear its route-derived assignment state.

        Args:
            package: Package to detach from this route.
            reason: Business reason for removing the package assignment.
            occurred_at: Business time at which the package was detached.

        Raises:
            EntityNotFoundError: If the package is not assigned to this route.
            DomainConflictError: if the package is assigned to this route but has no route reference.
        """
        for i, existing in enumerate(self._packages):
            if existing.package_id == package.package_id:
                route = existing.route
                if route is None:
                    raise DomainConflictError(
                        f"Package {existing.package_id} is present in route {self.route_id}'s "
                        "package list but has no route reference."
                    )
                self._packages.pop(i)
                previous_route_id = route.route_id
                previous_status = existing.status
                previous_location = existing.current_location
                previous_expected_arrival = existing.expected_arrival

                existing.reset_assignment_state()

                self._record_event(
                    PackageDetachedFromRoute(
                        package_id=existing.package_id,
                        previous_route_id=previous_route_id,
                        new_route_id=None,
                        previous_status=previous_status,
                        new_status=existing.status,
                        previous_location=previous_location,
                        new_location=existing.current_location,
                        previous_expected_arrival=previous_expected_arrival,
                        new_expected_arrival=existing.expected_arrival,
                        reason=reason,
                        occurred_at=occurred_at,
                    )
                )
                return
        raise EntityNotFoundError(
            f"Package with id {package.package_id} is not assigned to route {self.route_id}."
        )

    def assign_truck(self, truck: Truck, *, occurred_at: datetime) -> None:
        """Assign a truck to this route and record its assignment event.

        Args:
            truck: Free truck to assign. The truck's state is updated to reflect the assignment.
            occurred_at: Business time of the assignment, used for event timestamping.

        Raises:
            DomainConflictError: If either the route or truck is already assigned,
                or the truck has no known current location.
        """
        if self.truck is not None:
            raise DomainConflictError(
                f"Route {self.route_id} already has truck {self.truck.vehicle_id} assigned."
            )

        if not truck.is_free() or truck.route is not None:
            raise DomainConflictError(f"Truck {truck.vehicle_id} is already assigned to a route.")

        previous_status = truck.status
        previous_location = truck.current_location
        if previous_location is None:
            raise DomainConflictError(f"Truck {truck.vehicle_id} has no current location.")
        previous_busy_from = truck.busy_from
        previous_busy_until = truck.busy_until
        truck.assign(self)

        self.truck = truck

        self._record_event(
            TruckAssignedToRoute(
                truck_id=truck.vehicle_id,
                previous_route_id=None,
                new_route_id=self.route_id,
                previous_status=previous_status,
                new_status=truck.status,
                previous_location=previous_location,
                new_location=previous_location,
                previous_busy_from=previous_busy_from,
                new_busy_from=truck.busy_from,
                previous_busy_until=previous_busy_until,
                new_busy_until=truck.busy_until,
                occurred_at=occurred_at,
            )
        )

    def release_truck(
        self,
        *,
        now: datetime | None = None,
        force: bool = False,
        reason: TruckReleaseReason,
        occurred_at: datetime,
    ) -> bool:
        """Release the assigned truck if its route is complete or forced and record its release event.

        Args:
            now: Clock value used to decide whether the final ETA has passed.
            force: Release immediately even if the final ETA has not passed.
            reason: Business reason for releasing the truck.
            occurred_at: Business time at which the release occurred.

        Returns:
            True when a truck was released, false otherwise.

        Raises:
            DomainConflictError: If the route and truck assignment is inconsistent
                or the assigned truck has no known current location.
            RuntimeError: If a successful release does not produce a current location.
        """
        truck = self.truck
        if truck is None:
            return False

        truck_id = truck.vehicle_id
        truck_snapshot = truck.snapshot_state()
        if truck_snapshot.route is None:
            raise DomainConflictError(f"Truck {truck_id} cannot be released if not assigned to a route first.")
        if truck_snapshot.current_location is None:
            raise DomainConflictError(f"Truck {truck_id} has no current location.")

        released = truck.release(now=now, force=force)
        if not released:
            return False

        release_location = truck.current_location
        if release_location is None:
            truck.restore_state(truck_snapshot)
            raise RuntimeError("Released truck has no current location.")

        self.truck = None
        self._record_event(
            TruckReleasedFromRoute(
                truck_id=truck_id,
                previous_route_id=truck_snapshot.route.route_id,
                new_route_id=truck.route.route_id if truck.route is not None else None,
                previous_status=truck_snapshot.status,
                new_status=truck.status,
                previous_location=truck_snapshot.current_location,
                new_location=release_location,
                previous_busy_from=truck_snapshot.busy_from,
                new_busy_from=truck.busy_from,
                previous_busy_until=truck_snapshot.busy_until,
                new_busy_until=truck.busy_until,
                reason=reason,
                occurred_at=occurred_at,
            )
        )

        return True

    def total_assigned_weight(self) -> float:
        """Return the total weight of all currently assigned packages.

        Returns:
            Sum of assigned package weights in kilograms. This aggregate is
            distinct from the maximum simultaneous segment load.
        """
        return sum(package.weight for package in self._packages)

    def maximum_segment_load(self, extra_package: DeliveryPackage | None = None) -> float:
        """Return the heaviest cargo load carried on any route segment.

        Capacity is constrained by the maximum simultaneous load between two
        adjacent stops, not by the sum of every package assigned to the whole
        route. Assigned package entities and ``extra_package`` are reduced to
        immutable ``PackageLoad`` values before invoking the shared calculator.
        The candidate is included without mutating route assignment state.

        Args:
            extra_package: Optional package being evaluated for assignment.

        Returns:
            Maximum simultaneous carried weight across all adjacent route
            segments, in kilograms, or ``0.0`` when no segment carries load.
        """
        return RouteLoadCalculator.maximum_segment_load(
            locations=self._path.locations,
            packages=tuple(
                PackageLoad(
                    package.start_location,
                    package.end_location,
                    package.weight,
                )
                for package in self.packages
            ),
            extra_package=PackageLoad(
                extra_package.start_location, extra_package.end_location, extra_package.weight
            )
            if extra_package is not None
            else None,
        )

    def _update_expected_arrival(self, package: DeliveryPackage) -> None:
        if self._schedule is not None:
            package.expected_arrival = self._schedule.arrival_time_at(package.end_location)

    def restore_package_link(self, package: DeliveryPackage, *, refresh_expected_arrival: bool = True) -> None:
        """Restore a package-route link while rebuilding candidate snapshot state.

        Args:
            package: Candidate package to link to this candidate route.
            refresh_expected_arrival: Whether to recalculate the package ETA
                from this route's schedule.
        """
        if self._has_package(package):
            return

        self._packages.append(package)
        package.route = self
        if refresh_expected_arrival:
            self._update_expected_arrival(package)

    def _has_package(self, package: DeliveryPackage) -> bool:
        return any(existing.package_id == package.package_id for existing in self._packages)
