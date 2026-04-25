from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.domain.enums.route_status import RouteStatus
from src.domain.services.map import Map

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class RoutePosition:
    kind: str
    from_city: str | None = None
    to_city: str | None = None
    stop_city: str | None = None
    next_eta: datetime | None = None


class DeliveryRoute:
    SPEED_KMPH: int = 87

    def __init__(
        self,
        *locations: str,
        departure_time: datetime | None = None,
        route_id: int,
    ) -> None:
        if len(locations) < 2:
            raise ValueError("A route must have at least two locations.")

        valid = set(Map.get_locations())
        for location in locations:
            if location not in valid:
                raise ValueError(f"Invalid location code: {location}.")

        if len(set(locations)) != len(locations):
            raise ValueError("A route cannot contain duplicate locations.")

        self._locations: list[str] = list(locations)
        self._departure_time: datetime | None = departure_time
        self.route_id = route_id

        self.truck: Truck | None = None
        self._packages: list[DeliveryPackage] = []
        self.status: RouteStatus = RouteStatus.SCHEDULED if departure_time is not None else RouteStatus.PLANNED

        self._segments: list[tuple[str, str, int, timedelta]] = []
        self._stop_times: dict[str, datetime] = {}
        self._pos_index: dict[str, int] = {city: i for i, city in enumerate(self._locations)}

        if self._departure_time is not None:
            self._build_schedule()

    @property
    def departure_time(self) -> datetime | None:
        return self._departure_time

    @property
    def locations(self) -> list[str]:
        return list(self._locations)

    @property
    def start_location(self) -> str:
        return self._locations[0]

    @property
    def end_location(self) -> str:
        return self._locations[-1]

    @property
    def packages(self) -> list[DeliveryPackage]:
        return list(self._packages)

    @property
    def total_distance_km(self) -> int:
        if self._segments:
            return int(sum(km for _, _, km, _ in self._segments))

        return int(
            sum(Map.get_distance(a, b) for a, b in zip(self._locations, self._locations[1:], strict=False))
        )

    @property
    def eta_final(self) -> datetime | None:
        if self._departure_time is None:
            return None
        return self._stop_times[self._locations[-1]]

    def schedule(self, departure_time: datetime) -> None:
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

    def arrival_time_at(self, city: str) -> datetime:
        if self._departure_time is None:
            raise ValueError("Route not scheduled yet (no departure time).")
        if city not in self._stop_times:
            raise ValueError(f"City {city} is not on route {self.route_id}.")
        return self._stop_times[city]

    def current_position(self, now: datetime | None = None) -> RoutePosition:
        """Return a snapshot of the route's current position."""
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

    def includes_in_order(self, start: str, end: str) -> bool:
        return (
            start in self._pos_index
            and end in self._pos_index
            and self._pos_index[start] < self._pos_index[end]
        )

    def can_accept_package(self, package: DeliveryPackage, now: datetime | None = None) -> str | None:
        if error := self._validate_package_route_compatibility(package):
            return error

        if error := self._validate_pickup_not_passed(package, now):
            return error

        if error := self._validate_truck_constraints(extra_weight=package.weight):
            return error

        return None

    def assign_package(self, package: DeliveryPackage, now: datetime | None = None) -> None:
        if error := self.can_accept_package(package, now=now):
            raise ValueError(error)

        if package in self._packages:
            return

        self._packages.append(package)
        package.route = self
        self._update_expected_arrival(package)

    def detach_package(self, package: DeliveryPackage) -> None:
        for i, existing in enumerate(self._packages):
            if existing.package_id == package.package_id:
                self._packages.pop(i)
                if package.route is self:
                    package.reset_assignment_state()
                return
        raise ValueError(f"Package with id {package.package_id} is not assigned to route {self.route_id}.")

    def release_truck(self, *, now: datetime | None = None, force: bool = False) -> bool:
        if self.truck is None:
            return False

        truck = self.truck
        released = truck.release(now=now, force=force)
        if released or truck.route is None:
            self.truck = None
        return released

    def total_assigned_weight(self) -> float:
        return sum(package.weight for package in self._packages)

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

    def _validate_truck_constraints(self, extra_weight: float) -> str | None:
        if self.truck is None:
            return None

        total_after = self.total_assigned_weight() + extra_weight
        if total_after > self.truck.capacity:
            return (
                f"Truck {self.truck.vehicle_id} capacity exceeded: {total_after}kg > {self.truck.capacity}kg."
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

    def restore_package_link(self, package: DeliveryPackage) -> None:
        if package in self._packages:
            return

        self._packages.append(package)
        package.route = self
        self._update_expected_arrival(package)

    def info(self) -> str:
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
