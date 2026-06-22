"""Delivery route entity, schedule calculations, and assignment rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
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
from src.domain.value_objects.location_code import LocationCode

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.truck import Truck
    from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
    from src.domain.enums.truck_release_reasons import TruckReleaseReason
    from src.domain.events.base import DomainEvent


class RoutePositionKind(StrEnum):
    """Operational route position categories."""

    UNSCHEDULED = "UNSCHEDULED"
    BEFORE_START = "BEFORE_START"
    AT_STOP = "AT_STOP"
    IN_TRANSIT = "IN_TRANSIT"
    AFTER_END = "AFTER_END"


@dataclass(frozen=True, slots=True)
class RoutePosition:
    """Current operational position of a scheduled route."""

    kind: RoutePositionKind
    from_city: LocationCode | None = None
    to_city: LocationCode | None = None
    stop_city: LocationCode | None = None
    next_eta: datetime | None = None


@dataclass(frozen=True, slots=True)
class RouteSegment:
    """Travel segment between two adjacent route stops."""

    start: LocationCode
    end: LocationCode
    distance_km: int
    duration: timedelta


@dataclass(frozen=True, slots=True)
class RouteStateSnapshot:
    """Captured mutable state for restoring a route after a failed operation."""

    departure_time: datetime | None
    status: RouteStatus
    truck: Truck | None
    packages: tuple[DeliveryPackage, ...]


class DeliveryRoute(DomainEventRecorderMixin):
    """Route aggregate for packages and an optional assigned truck."""

    SPEED_KMPH: int = 87

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
            DomainValidationError: If fewer than two locations are supplied, any location is
                unknown, or a location is repeated.
        """
        self._locations = self._normalize_locations(locations)
        self._departure_time: datetime | None = departure_time
        self.route_id = route_id

        self.truck: Truck | None = None
        self._packages: list[DeliveryPackage] = []
        self.status: RouteStatus = RouteStatus.SCHEDULED if departure_time is not None else RouteStatus.PLANNED

        self._segments: list[RouteSegment] = []
        self._stop_times: dict[LocationCode, datetime] = {}
        self._pos_index: dict[LocationCode, int] = {city: i for i, city in enumerate(self._locations)}

        if self._departure_time is not None:
            self._build_schedule()

        self._pending_events: list[DomainEvent] = []

    def _normalize_locations(self, locations: tuple[str | LocationCode, ...]) -> list[LocationCode]:
        """Normalize and validate route locations."""
        if len(locations) < 2:
            raise DomainValidationError("A route must have at least two locations.")

        typed_locations = [LocationCode(location) for location in locations]
        valid_locations = set(Map.get_locations())
        invalid_locations = [location for location in typed_locations if location not in valid_locations]
        if invalid_locations:
            raise DomainValidationError(f"Invalid location code: {invalid_locations[0]}.")

        if len(set(typed_locations)) != len(typed_locations):
            raise DomainValidationError("A route cannot contain duplicate locations.")

        return typed_locations

    @property
    def departure_time(self) -> datetime | None:
        """Scheduled departure time, or None while the route is planned."""
        return self._departure_time

    @property
    def locations(self) -> list[LocationCode]:
        """Route locations in travel order."""
        return list(self._locations)

    @property
    def start_location(self) -> LocationCode:
        """First location on the route."""
        return self._locations[0]

    @property
    def end_location(self) -> LocationCode:
        """Final location on the route."""
        return self._locations[-1]

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
            DomainValidationError: If fewer than two locations are supplied, any location is
                unknown, or a location is repeated.
        """
        route = cls(*locations, departure_time=departure_time, route_id=route_id)

        route._record_event(
            RouteCreated(
                route_id=route.route_id,
                locations=tuple(route.locations),
                departure_time=route.departure_time,
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

        self.status = RouteStatus.IN_PROGRESS
        self._record_event(
            RouteStarted(
                route_id=self.route_id,
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

        self.status = RouteStatus.COMPLETED
        self._record_event(
            RouteCompleted(
                route_id=self.route_id,
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
            departure_time=self._departure_time,
            status=self.status,
            truck=self.truck,
            packages=tuple(self._packages),
        )

    def restore_state(self, snapshot: RouteStateSnapshot) -> None:
        """Restore mutable route state from a prior snapshot.

        Args:
            snapshot: State captured by `snapshot_state`.
        """
        self._departure_time = snapshot.departure_time
        self.status = snapshot.status
        self.truck = snapshot.truck
        self._packages = list(snapshot.packages)
        self._segments.clear()
        self._stop_times.clear()

        if self._departure_time is not None:
            self._build_schedule()

    @property
    def total_distance_km(self) -> int:
        """Total travel distance in kilometres."""
        if self._segments:
            return int(sum(segment.distance_km for segment in self._segments))

        return int(sum(Map.get_distance(start, end) for start, end in pairwise(self._locations)))

    @property
    def eta_final(self) -> datetime | None:
        """Expected arrival time at the final stop, if scheduled."""
        return self._stop_times.get(self.end_location)

    def schedule(self, departure_time: datetime, *, occurred_at: datetime) -> None:
        """Schedule the route, rebuild stop timing information, and record a `RouteScheduled` event.

        Args:
            departure_time: Departure time for the first route location.
            occurred_at: Business time at which the route is scheduled successfully.

        Raises:
            DomainConflictError: If route is already scheduled.
            RuntimeError: If a scheduled route has no expected completion time.
        """
        if self.departure_time is not None:
            raise DomainConflictError(f"Route {self.route_id} is already scheduled.")

        self._departure_time = departure_time
        self._build_schedule()
        self.status = RouteStatus.SCHEDULED

        expected_completion_time = self.eta_final
        if expected_completion_time is None:
            raise RuntimeError("Scheduled route has no expected completion time.")

        self._record_event(
            RouteScheduled(
                route_id=self.route_id,
                departure_time=departure_time,
                expected_completion_time=expected_completion_time,
                occurred_at=occurred_at,
            )
        )

    def _build_schedule(self) -> None:
        if self._departure_time is None:
            raise DomainConflictError("Cannot build schedule without a departure time.")

        self._segments.clear()
        self._stop_times.clear()

        current_time = self._departure_time
        self._stop_times[self.start_location] = current_time

        for start, end in pairwise(self._locations):
            distance_km = Map.get_distance(start, end)
            duration = timedelta(hours=distance_km / DeliveryRoute.SPEED_KMPH)
            self._segments.append(RouteSegment(start, end, distance_km, duration))
            current_time += duration
            self._stop_times[end] = current_time

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
        if self._departure_time is None:
            raise DomainConflictError("Route not scheduled yet (no departure time).")
        city = LocationCode(city)
        if city not in self._stop_times:
            raise DomainValidationError(f"City {city} is not on route {self.route_id}.")
        return self._stop_times[city]

    def current_position(self, now: datetime | None = None) -> RoutePosition:
        """Return a snapshot of the route's current position.

        Args:
            now: Clock value used to evaluate route progress. Uses current time
                when omitted.

        Returns:
            Position descriptor for the route at the requested time.
        """
        if self._departure_time is None:
            return RoutePosition(kind=RoutePositionKind.UNSCHEDULED, stop_city=self.start_location)

        now = now or datetime.now()
        first_city = self.start_location
        first_departure = self._stop_times[first_city]

        if now < first_departure:
            return RoutePosition(
                kind=RoutePositionKind.BEFORE_START, stop_city=first_city, next_eta=first_departure
            )

        for segment in self._segments:
            position = self._position_on_segment(segment, now, first_city)
            if position is not None:
                return position

        return self._position_after_segments(now, first_departure)

    def _position_on_segment(
        self,
        segment: RouteSegment,
        now: datetime,
        first_city: LocationCode,
    ) -> RoutePosition | None:
        start_time = self._stop_times[segment.start]
        end_time = self._stop_times[segment.end]

        if now == start_time:
            return RoutePosition(
                kind=(
                    RoutePositionKind.IN_TRANSIT if segment.start == first_city else RoutePositionKind.AT_STOP
                ),
                from_city=segment.start,
                to_city=segment.end,
                next_eta=end_time,
            )

        if now == end_time:
            return RoutePosition(
                kind=RoutePositionKind.AT_STOP,
                stop_city=segment.end,
                next_eta=self._next_stop_eta(segment.end),
            )

        if start_time < now < end_time:
            return RoutePosition(
                kind=RoutePositionKind.IN_TRANSIT,
                from_city=segment.start,
                to_city=segment.end,
                next_eta=end_time,
            )

        return None

    def _next_stop_eta(self, city: LocationCode) -> datetime | None:
        next_index = self._pos_index[city] + 1
        if next_index >= len(self._locations):
            return None
        return self._stop_times.get(self._locations[next_index])

    def _position_after_segments(self, now: datetime, first_departure: datetime) -> RoutePosition:
        return (
            RoutePosition(kind=RoutePositionKind.AFTER_END, stop_city=self.end_location)
            if now >= self._stop_times[self.end_location]
            else RoutePosition(
                kind=RoutePositionKind.AT_STOP,
                stop_city=self.start_location,
                next_eta=first_departure,
            )
        )

    def includes_in_order(self, start: str | LocationCode, end: str | LocationCode) -> bool:
        """Return whether the route visits start before end.

        Args:
            start: Candidate raw or typed pickup location code.
            end: Candidate raw or typed delivery location code.

        Returns:
            True when both locations are present and start appears before end.
        """
        start_code = LocationCode(start)
        end_code = LocationCode(end)
        return (
            start_code in self._pos_index
            and end_code in self._pos_index
            and self._pos_index[start_code] < self._pos_index[end_code]
        )

    def can_accept_package(self, package: DeliveryPackage, now: datetime | None = None) -> str | None:
        """Validate whether a package can be assigned to this route.

        Args:
            package: Package being evaluated.
            now: Clock value used for live pickup-pass validation.

        Returns:
            None when the package is acceptable, otherwise a human-readable
            rejection reason.
        """
        if error := self._validate_package_route_compatibility(package):
            return error

        if error := self._validate_pickup_not_passed(package, now):
            return error

        if error := self._validate_truck_constraints(extra_package=package):
            return error

        return None

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
        if error := self.can_accept_package(package, now=now):
            raise DomainConflictError(error)

        if self._has_package(package):
            return

        self._packages.append(package)
        package.route = self
        self._update_expected_arrival(package)

        self._record_event(
            PackageAssignedToRoute(
                route_id=self.route_id,
                package_id=package.package_id,
                expected_arrival=package.expected_arrival,
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
        """
        for i, existing in enumerate(self._packages):
            if existing.package_id == package.package_id:
                self._packages.pop(i)
                if package.route is self:
                    package.reset_assignment_state()

                self._record_event(
                    PackageDetachedFromRoute(
                        route_id=self.route_id,
                        package_id=existing.package_id,
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
            DomainConflictError: If a truck is already assigned to this route.
        """
        if self.truck is not None:
            raise DomainConflictError(
                f"Route {self.route_id} already has truck {self.truck.vehicle_id} assigned."
            )

        if not truck.is_free() or truck.route is not None:
            raise DomainConflictError(f"Truck {truck.vehicle_id} is already assigned to a route.")

        truck.assign(self)

        self.truck = truck
        self._record_event(
            TruckAssignedToRoute(
                route_id=self.route_id,
                truck_id=truck.vehicle_id,
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
            RuntimeError: If released truck has no current location.
        """
        truck = self.truck
        if truck is None:
            return False

        truck_id = truck.vehicle_id
        truck_snapshot = truck.snapshot_state()
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
                route_id=self.route_id,
                truck_id=truck_id,
                release_location=release_location,
                reason=reason,
                occurred_at=occurred_at,
            )
        )

        return True

    def total_assigned_weight(self) -> float:
        """Total weight of currently assigned packages."""
        return sum(package.weight for package in self._packages)

    def maximum_segment_load(self, extra_package: DeliveryPackage | None = None) -> float:
        """Return the heaviest cargo load carried on any route segment.

        Capacity is constrained by the maximum simultaneous load between two
        adjacent stops, not by the sum of every package assigned to the whole
        route. `extra_package` is included as a candidate load without mutating
        route state.

        Args:
            extra_package: Optional package being evaluated for assignment.

        Returns:
            Maximum carried weight across all adjacent route segments.
        """
        if len(self._locations) < 2:
            return 0.0

        segment_loads = [0.0] * (len(self._locations) - 1)
        packages = [*self._packages]
        if extra_package is not None:
            packages.append(extra_package)

        for package in packages:
            start_index = self._pos_index.get(package.start_location)
            end_index = self._pos_index.get(package.end_location)
            if start_index is None or end_index is None or start_index >= end_index:
                continue

            for segment_index in range(start_index, end_index):
                segment_loads[segment_index] += package.weight

        return max(segment_loads, default=0.0)

    def _validate_package_route_compatibility(self, package: DeliveryPackage) -> str | None:
        if package.start_location not in self._pos_index or package.end_location not in self._pos_index:
            return (
                f"Route {self.route_id} does not include start/end of "
                f"package {package.package_id} ({package.start_location} -> {package.end_location})."
            )

        if not self.includes_in_order(package.start_location, package.end_location):
            return (
                f"Route {self.route_id} does not pass from {package.start_location} "
                f"to {package.end_location} in order for package {package.package_id}."
            )

        return None

    def _validate_pickup_not_passed(self, package: DeliveryPackage, now: datetime | None) -> str | None:
        if now is None or self._departure_time is None:
            return None

        pickup_index = self._pos_index[package.start_location]
        position = self.current_position(now)

        if position.kind in {RoutePositionKind.UNSCHEDULED, RoutePositionKind.BEFORE_START}:
            return None

        if position.kind == RoutePositionKind.AT_STOP:
            stop_city = position.stop_city
            if stop_city and self._pos_index[stop_city] > pickup_index:
                return self._pickup_passed_error(package)
            return None

        if position.kind == RoutePositionKind.IN_TRANSIT:
            from_city = position.from_city
            if from_city and self._pos_index[from_city] >= pickup_index:
                return self._pickup_passed_error(package)
            return None

        if position.kind == RoutePositionKind.AFTER_END:
            return self._pickup_passed_error(package)

        return None

    def _pickup_passed_error(self, package: DeliveryPackage) -> str:
        return (
            f"Route {self.route_id} has already passed pickup location "
            f"{package.start_location} for package {package.package_id}."
        )

    def _validate_truck_constraints(self, extra_package: DeliveryPackage) -> str | None:
        if self.truck is None:
            return None

        max_segment_load = self.maximum_segment_load(extra_package=extra_package)
        if max_segment_load > self.truck.capacity:
            return (
                f"Truck {self.truck.vehicle_id} capacity exceeded: "
                f"segment load {max_segment_load}kg > {self.truck.capacity}kg."
            )

        if self.truck.max_range < self.total_distance_km:
            return (
                f"Truck {self.truck.vehicle_id} lacks range for {self.total_distance_km} km "
                f"(range: {self.truck.max_range} km)."
            )

        return None

    def _update_expected_arrival(self, package: DeliveryPackage) -> None:
        if self._departure_time and package.end_location in self._stop_times:
            package.expected_arrival = self.arrival_time_at(package.end_location)

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
