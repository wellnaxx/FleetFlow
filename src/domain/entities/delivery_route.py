"""Delivery route entity, schedule calculations, and assignment rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.domain.enums.route_status import RouteStatus
from src.domain.services.map import Map
from src.domain.value_objects.location_code import LocationCode

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class RoutePosition:
    """Current operational position of a scheduled route."""

    kind: str
    from_city: LocationCode | None = None
    to_city: LocationCode | None = None
    stop_city: LocationCode | None = None
    next_eta: datetime | None = None


@dataclass(frozen=True)
class RouteStateSnapshot:
    """Captured mutable state for restoring a route after a failed operation."""

    departure_time: datetime | None
    status: RouteStatus
    truck: Truck | None
    packages: tuple[DeliveryPackage, ...]


class DeliveryRoute:
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
            ValueError: If fewer than two locations are supplied, any location is
                unknown, or a location is repeated.
        """
        if len(locations) < 2:
            raise ValueError("A route must have at least two locations.")

        typed_locations = [LocationCode(location) for location in locations]
        valid = set(Map.get_locations())
        for location in typed_locations:
            if location not in valid:
                raise ValueError(f"Invalid location code: {location}.")

        if len(set(typed_locations)) != len(typed_locations):
            raise ValueError("A route cannot contain duplicate locations.")

        self._locations: list[LocationCode] = typed_locations
        self._departure_time: datetime | None = departure_time
        self.route_id = route_id

        self.truck: Truck | None = None
        self._packages: list[DeliveryPackage] = []
        self.status: RouteStatus = RouteStatus.SCHEDULED if departure_time is not None else RouteStatus.PLANNED

        self._segments: list[tuple[LocationCode, LocationCode, int, timedelta]] = []
        self._stop_times: dict[LocationCode, datetime] = {}
        self._pos_index: dict[LocationCode, int] = {city: i for i, city in enumerate(self._locations)}

        if self._departure_time is not None:
            self._build_schedule()

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
    def packages(self) -> list[DeliveryPackage]:
        """Assigned packages as a copy of the internal collection."""
        return list(self._packages)

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
            return int(sum(km for _, _, km, _ in self._segments))

        return int(
            sum(Map.get_distance(a, b) for a, b in zip(self._locations, self._locations[1:], strict=False))
        )

    @property
    def eta_final(self) -> datetime | None:
        """Expected arrival time at the final stop, if scheduled."""
        if self._departure_time is None:
            return None
        return self._stop_times[self._locations[-1]]

    def schedule(self, departure_time: datetime) -> None:
        """Schedule the route and rebuild stop timing information.

        Args:
            departure_time: Departure time for the first route location.
        """
        self._departure_time = departure_time
        self._build_schedule()
        self.status = RouteStatus.SCHEDULED

    def _build_schedule(self) -> None:
        if self._departure_time is None:
            raise ValueError("Cannot build schedule without a departure time.")

        self._segments.clear()
        self._stop_times.clear()

        current_time = self._departure_time
        self._stop_times[self._locations[0]] = current_time

        for start, end in zip(self._locations, self._locations[1:], strict=False):
            distance_km = Map.get_distance(start, end)
            duration = timedelta(hours=distance_km / DeliveryRoute.SPEED_KMPH)
            self._segments.append((start, end, distance_km, duration))
            current_time += duration
            self._stop_times[end] = current_time

    def arrival_time_at(self, city: str | LocationCode) -> datetime:
        """Return the scheduled arrival time for a route city.

        Args:
            city: Raw or typed location code on this route.

        Returns:
            Scheduled arrival time at the requested city.

        Raises:
            ValueError: If the route is unscheduled or the city is not on it.
        """
        if self._departure_time is None:
            raise ValueError("Route not scheduled yet (no departure time).")
        city = LocationCode(city)
        if city not in self._stop_times:
            raise ValueError(f"City {city} is not on route {self.route_id}.")
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
            return RoutePosition(kind="UNSCHEDULED", stop_city=self.start_location)

        now = now or datetime.now()
        first_city = self.start_location
        first_departure = self._stop_times[first_city]

        if now < first_departure:
            return RoutePosition(kind="BEFORE_START", stop_city=first_city, next_eta=first_departure)

        for start, end, _, _ in self._segments:
            start_time = self._stop_times[start]
            end_time = self._stop_times[end]

            if now == start_time:
                if start == first_city:
                    return RoutePosition(kind="IN_TRANSIT", from_city=start, to_city=end, next_eta=end_time)
                return RoutePosition(kind="AT_STOP", stop_city=start, next_eta=end_time)

            if now == end_time:
                next_eta = None
                index = self._pos_index[end]
                if index + 1 < len(self._locations):
                    next_eta = self._stop_times[self._locations[index + 1]]
                return RoutePosition(kind="AT_STOP", stop_city=end, next_eta=next_eta)

            if start_time < now < end_time:
                return RoutePosition(kind="IN_TRANSIT", from_city=start, to_city=end, next_eta=end_time)

        if now >= self._stop_times[self.end_location]:
            return RoutePosition(kind="AFTER_END", stop_city=self.end_location)

        return RoutePosition(kind="AT_STOP", stop_city=first_city, next_eta=first_departure)

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

    def assign_package(self, package: DeliveryPackage, now: datetime | None = None) -> None:
        """Assign a package after validating route compatibility.

        Args:
            package: Package to assign.
            now: Clock value used for live pickup-pass validation.

        Raises:
            ValueError: If the package is incompatible with the route.
        """
        if error := self.can_accept_package(package, now=now):
            raise ValueError(error)

        if package in self._packages:
            return

        self._packages.append(package)
        package.route = self
        self._update_expected_arrival(package)

    def detach_package(self, package: DeliveryPackage) -> None:
        """Detach a package and clear its route-derived assignment state.

        Args:
            package: Package to detach from this route.

        Raises:
            ValueError: If the package is not assigned to this route.
        """
        for i, existing in enumerate(self._packages):
            if existing.package_id == package.package_id:
                self._packages.pop(i)
                if package.route is self:
                    package.reset_assignment_state()
                return
        raise ValueError(f"Package with id {package.package_id} is not assigned to route {self.route_id}.")

    def release_truck(self, *, now: datetime | None = None, force: bool = False) -> bool:
        """Release the assigned truck if its route is complete or forced.

        Args:
            now: Clock value used to decide whether the final ETA has passed.
            force: Release immediately even if the final ETA has not passed.

        Returns:
            True when a truck was released, false otherwise.
        """
        if self.truck is None:
            return False

        truck = self.truck
        released = truck.release(now=now, force=force)
        if released or truck.route is None:
            self.truck = None
        return released

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

        segment_loads = [0.0 for _ in range(len(self._locations) - 1)]
        for package in (*self._packages, *(() if extra_package is None else (extra_package,))):
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

        if position.kind in {"UNSCHEDULED", "BEFORE_START"}:
            return None

        if position.kind == "AT_STOP":
            stop_city = position.stop_city
            if stop_city is None:
                return None
            if self._pos_index[stop_city] > pickup_index:
                return self._pickup_passed_error(package)
            return None

        if position.kind == "IN_TRANSIT":
            from_city = position.from_city
            if from_city is None:
                return None
            if self._pos_index[from_city] >= pickup_index:
                return self._pickup_passed_error(package)
            return None

        if position.kind == "AFTER_END":
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
        if self._departure_time is None:
            return

        if package.end_location in self._stop_times:
            package.expected_arrival = self.arrival_time_at(package.end_location)

    def restore_package_link(self, package: DeliveryPackage, *, refresh_expected_arrival: bool = True) -> None:
        """Restore a package-route link while rebuilding candidate snapshot state.

        Args:
            package: Candidate package to link to this candidate route.
            refresh_expected_arrival: Whether to recalculate the package ETA
                from this route's schedule.
        """
        if package in self._packages:
            return

        self._packages.append(package)
        package.route = self
        if refresh_expected_arrival:
            self._update_expected_arrival(package)

    def info(self) -> str:
        """Return a human-readable route summary.

        Returns:
            Multi-line route description for CLI display.
        """
        lines: list[str] = []
        lines.append(f"Route ID: {self.route_id}")
        lines.append(f"Truck ID: {self.truck.vehicle_id if self.truck else 'Not assigned'}")
        lines.append(f"Start: {self.start_location}")
        lines.append(f"End: {self.end_location}")

        if self._departure_time is None:
            lines.append("Departure: (unscheduled)")
        else:
            lines.append(f"Departure: {self._departure_time.strftime('%Y-%m-%d %H:%M')}")

        lines.append(f"Total Distance: {self.total_distance_km} km")

        if self._departure_time is not None:
            lines.append("Stops:")
            for city in self._locations:
                stop_time = self._stop_times[city]
                lines.append(f"  - {city} @ {stop_time.strftime('%Y-%m-%d %H:%M')}")

            pos = self.current_position()
            if pos.kind == "BEFORE_START":
                eta_str = pos.next_eta.strftime("%Y-%m-%d %H:%M") if pos.next_eta else "N/A"
                lines.append(f"Status: BEFORE_START (next {pos.stop_city} @ {eta_str})")
            elif pos.kind == "AT_STOP":
                lines.append(f"Status: AT_STOP ({pos.stop_city})")
            elif pos.kind == "IN_TRANSIT":
                eta_str = pos.next_eta.strftime("%Y-%m-%d %H:%M") if pos.next_eta else "N/A"
                lines.append(f"Status: IN_TRANSIT ({pos.from_city} -> {pos.to_city}), ETA {eta_str}")
            else:
                lines.append("Status: AFTER_END")
        else:
            lines.append("Status: PLANNED (unscheduled)")

        lines.append(f"Assigned weight: {self.total_assigned_weight():.2f} kg")
        return "\n".join(lines)
