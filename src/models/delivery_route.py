from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from src.models.map import Map

try:
    from src.models.truck import Truck
except Exception:
    Truck = object  # type: ignore
try:
    from src.models.delivery_package import DeliveryPackage
except Exception:
    DeliveryPackage = object  # type: ignore

@dataclass(frozen=True)
class RoutePosition:
    kind: str
    from_city: Optional[str] = None
    to_city: Optional[str] = None
    stop_city: Optional[str] = None
    next_eta: Optional[datetime] = None

class DeliveryRoute:
    _next_id = 1
    SPEED_KMPH = 87

    def __init__(self, *locations: str, departure_time: Optional[datetime] = None, route_id: int | None = None):
        if len(locations) < 2:
            raise ValueError("A route must have at least two locations.")
        valid = set(Map.get_locations())
        for c in locations:
            if c not in valid:
                raise ValueError(f"Invalid location code: {c}.")
        self._locations: List[str] = list(locations)
        self._departure_time: Optional[datetime] = departure_time
        if route_id is None:
            route_id = DeliveryRoute._next_id
            DeliveryRoute._next_id += 1
        self.route_id = route_id

        self.truck: Optional[Truck] = None
        self._packages: List[DeliveryPackage] = []

        self._segments: List[Tuple[str, str, int, timedelta]] = []
        self._stop_times: Dict[str, datetime] = {}
        self._pos_index: Dict[str, int] = {city: i for i, city in enumerate(self._locations)}

        if self._departure_time is not None:
            self._build_schedule()

    @property
    def departure_time(self) -> Optional[datetime]:
        return self._departure_time

    def schedule(self, departure_time: datetime) -> None:
        """Set (or reset) the departure time and rebuild schedule."""
        self._departure_time = departure_time
        self._build_schedule()

    def _build_schedule(self) -> None:
        if self._departure_time is None:
            raise ValueError("Cannot build schedule without a departure time.")
        self._segments.clear()
        self._stop_times.clear()
        curr = self._departure_time
        self._stop_times[self._locations[0]] = curr
        for a, b in zip(self._locations, self._locations[1:]):
            dist = Map.get_distance(a, b)
            dur = timedelta(hours=dist / DeliveryRoute.SPEED_KMPH)
            self._segments.append((a, b, dist, dur))
            curr = curr + dur
            self._stop_times[b] = curr

    @property
    def locations(self) -> List[str]:
        return list(self._locations)

    @property
    def start_location(self) -> str:
        return self._locations[0]

    @property
    def end_location(self) -> str:
        return self._locations[-1]

    @property
    def total_distance_km(self) -> int:
        if self._segments:
            return int(sum(k for _, _, k, _ in self._segments))
        return int(sum(Map.get_distance(a, b) for a, b in zip(self._locations, self._locations[1:])))

    def arrival_time_at(self, city: str) -> datetime:
        if self._departure_time is None:
            raise ValueError("Route not scheduled yet (no departure time).")
        if city not in self._stop_times:
            raise ValueError(f"City {city} is not on route {self.route_id}.")
        return self._stop_times[city]

    @property
    def eta_final(self) -> Optional[datetime]:
        if self._departure_time is None:
            return None
        return self._stop_times[self._locations[-1]]

    def current_position(self, now: Optional[datetime] = None) -> RoutePosition:
        """Compute the route's current position snapshot.

        Boundary rules:
            * ``now < departure_time`` → ``BEFORE_START``
            * ``now == arrival[k]`` → ``AT_STOP`` at that city
            * ``arrival[k] < now < arrival[k+1]`` → ``IN_TRANSIT`` on leg k→k+1
            * ``now > final_arrival`` → ``AFTER_END``

        Exact arrivals prefer ``AT_STOP``; progress is clamped to ``[0, leg_km]``.

        Returns:
            dict with keys:
                - kind: 'BEFORE_START' | 'IN_TRANSIT' | 'AT_STOP' | 'AFTER_END'
                - leg_index: int or None
                - from_city, to_city: present for ``IN_TRANSIT``
                - progress_km: float for ``IN_TRANSIT``
                - arrived_city: str for ``AT_STOP``
        """
        if self._departure_time is None:
            return RoutePosition(kind="UNSCHEDULED", stop_city=self._locations[0])

        now = now or datetime.now()
        first = self._locations[0]
        first_depart = self._stop_times[first]

        if now < first_depart:
            return RoutePosition(kind="BEFORE_START", stop_city=first, next_eta=first_depart)

        for (a, b, _, _) in self._segments:
            ta, tb = self._stop_times[a], self._stop_times[b]

            if now == ta:
                if a == first:
                    return RoutePosition(kind="IN_TRANSIT", from_city=a, to_city=b, next_eta=tb)
                return RoutePosition(kind="AT_STOP", stop_city=a, next_eta=tb)

            if now == tb:
                nxt_eta = None
                idx = self._pos_index[b]
                if idx + 1 < len(self._locations):
                    nxt_eta = self._stop_times[self._locations[idx + 1]]
                return RoutePosition(kind="AT_STOP", stop_city=b, next_eta=nxt_eta)

            if ta < now < tb:
                return RoutePosition(kind="IN_TRANSIT", from_city=a, to_city=b, next_eta=tb)

        last = self._locations[-1]
        if now >= self._stop_times[last]:
            return RoutePosition(kind="AFTER_END", stop_city=last)

        return RoutePosition(kind="AT_STOP", stop_city=first, next_eta=first_depart)

    @property
    def packages(self) -> List[DeliveryPackage]:
        return list(self._packages)

    def includes_in_order(self, start: str, end: str) -> bool:
        pos = self._pos_index
        return start in pos and end in pos and pos[start] < pos[end]

    def can_accept_package(self, package: DeliveryPackage) -> Optional[str]:
        s = getattr(package, "start_location", None)
        e = getattr(package, "end_location", None)
        if s not in self._pos_index or e not in self._pos_index:
            return (f"Route {self.route_id} does not include start/end of "
                    f"package {getattr(package,'package_id','?')} ({s} -> {e}).")
        if not self.includes_in_order(s, e):
            return (f"Route {self.route_id} does not pass from {s} to {e} in order "
                    f"for package {getattr(package,'package_id','?')}.")

        if self.truck:
            total_after = self.total_assigned_weight() + float(getattr(package, "weight", 0.0))
            if total_after > float(getattr(self.truck, "capacity", 0.0)):
                return (f"Truck {getattr(self.truck,'vehicle_id','?')} capacity exceeded: "
                        f"{total_after}kg > {self.truck.capacity}kg.")
            if float(getattr(self.truck, "max_range", 0.0)) < float(self.total_distance_km):
                return (f"Truck {self.truck.vehicle_id} lacks range for {self.total_distance_km} km "
                        f"(range: {self.truck.max_range} km).")
        return None

    def can_accept_packages(self, packages: List[DeliveryPackage]) -> List[str]:
        errors: List[str] = []
        for package in packages:
            s = getattr(package, "start_location", None)
            e = getattr(package, "end_location", None)
            if s not in self._pos_index or e not in self._pos_index:
                errors.append(
                    f"Route {self.route_id} does not include start/end of "
                    f"package {getattr(package,'package_id','?')} ({s} -> {e})."
                )
            elif not self.includes_in_order(s, e):
                errors.append(
                    f"Route {self.route_id} does not pass from {s} to {e} in order "
                    f"for package {getattr(package,'package_id','?')}."
                )
        if self.truck:
            total_after = self.total_assigned_weight() + sum(float(getattr(p, "weight", 0.0)) for p in packages)
            if total_after > float(getattr(self.truck, "capacity", 0.0)):
                errors.append(
                    f"Truck {self.truck.vehicle_id} capacity exceeded: "
                    f"{total_after}kg > {self.truck.capacity}kg."
                )
            if float(getattr(self.truck, "max_range", 0.0)) < float(self.total_distance_km):
                errors.append(
                    f"Truck {self.truck.vehicle_id} lacks range for {self.total_distance_km} km "
                    f"(range: {self.truck.max_range} km)."
                )
        return errors

    def assign_package(self, package: DeliveryPackage) -> None:
        err = self.can_accept_package(package)
        if err:
            raise ValueError(err)
        if package in self._packages:
            return
        self._packages.append(package)
        package.route = self
        if self._departure_time is not None:
            try:
                eta = self.arrival_time_at(getattr(package, "end_location", self.end_location))
                setattr(package, "expected_arrival", eta)
            except Exception:
                pass

    def assign_packages(self, packages: List[DeliveryPackage]) -> None:
        errs = self.can_accept_packages(packages)
        if errs:
            raise ValueError("Bulk assignment failed:\n- " + "\n- ".join(errs))
        for p in packages:
            if p in self._packages:
                continue
            self._packages.append(p)
            p.route = self
            if self._departure_time is not None:
                try:
                    setattr(p, "expected_arrival", self.arrival_time_at(getattr(p, "end_location", self.end_location)))
                except Exception:
                    pass

    def total_assigned_weight(self) -> float:
        return sum(float(getattr(p, "weight", 0.0)) for p in self._packages)

    def info(self) -> str:
        lines = []
        lines.append(f"Route ID: {self.route_id}")
        lines.append(f"Truck ID: {getattr(self.truck, 'vehicle_id', 'Not assigned')}")
        lines.append(f"Start: {self.start_location}")
        lines.append(f"End: {self.end_location}")
        if self._departure_time is None:
            lines.append("Departure: (unscheduled)")
        else:
            lines.append(f"Departure: {self._departure_time.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Total Distance: {self.total_distance_km} km")
        if self._departure_time is not None:
            lines.append("Stops:")
            for c in self._locations:
                t = self._stop_times.get(c)
                lines.append(f"  - {c} @ {t.strftime('%Y-%m-%d %H:%M')}")
            pos = self.current_position()
            if pos.kind == "BEFORE_START":
                lines.append(f"Status: BEFORE_START (next {pos.stop_city} @ {pos.next_eta.strftime('%Y-%m-%d %H:%M')})")
            elif pos.kind == "AT_STOP":
                lines.append(f"Status: AT_STOP ({pos.stop_city})")
            elif pos.kind == "IN_TRANSIT":
                lines.append(f"Status: IN_TRANSIT ({pos.from_city} → {pos.to_city}), ETA {pos.next_eta.strftime('%Y-%m-%d %H:%M')}")
            else:
                lines.append("Status: AFTER_END")
        else:
            lines.append("Status: PLANNED (unscheduled)")
        lines.append(f"Assigned weight: {self.total_assigned_weight():.2f} kg")
        return "\n".join(lines)
