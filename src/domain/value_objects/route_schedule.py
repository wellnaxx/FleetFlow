"""Immutable route schedules, travel segments, and temporal position values."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType

from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.shared.validation import require_naive_datetime


class RoutePositionKind(StrEnum):
    """Operational route position categories."""

    UNSCHEDULED = "UNSCHEDULED"
    BEFORE_START = "BEFORE_START"
    AT_STOP = "AT_STOP"
    IN_TRANSIT = "IN_TRANSIT"
    AFTER_END = "AFTER_END"


@dataclass(frozen=True, slots=True)
class RoutePosition:
    """Operational position of a route at a specific business time.

    Attributes:
        kind: Position category describing the route's temporal state.
        from_city: Segment origin while the route is in transit.
        to_city: Segment destination while the route is in transit.
        stop_city: Current stop when the route is stationary.
        next_eta: Scheduled arrival time at the next stop, when available.
    """

    kind: RoutePositionKind
    from_city: LocationCode | None = None
    to_city: LocationCode | None = None
    stop_city: LocationCode | None = None
    next_eta: datetime | None = None


@dataclass(frozen=True, slots=True)
class RouteSegment:
    """Calculated travel segment between two adjacent route stops.

    Attributes:
        start: Segment origin.
        end: Segment destination.
        distance_km: Travel distance in kilometres.
        duration: Travel time calculated for the scheduling speed.
    """

    start: LocationCode
    end: LocationCode
    distance_km: int
    duration: timedelta


@dataclass(frozen=True, slots=True)
class ScheduledStop:
    """Location and calculated arrival time within a route schedule.

    Attributes:
        location: Scheduled route location.
        arrival_at: Business-local arrival time at the location.
    """

    location: LocationCode
    arrival_at: datetime


@dataclass(frozen=True, slots=True)
class RouteSchedule:
    """Immutable calculated timing information for an ordered route path.

    The ordered stop and segment tuples are the source of truth. Private,
    read-only mappings provide constant-time arrival and stop-index lookups.

    Attributes:
        departure_time: Business-local departure time from the first stop.
        segments: Travel segments in route order.
        stops: Scheduled stops in route order, including the departure stop.
    """

    departure_time: datetime
    segments: tuple[RouteSegment, ...]
    stops: tuple[ScheduledStop, ...]

    _arrival_times: Mapping[LocationCode, datetime] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _stop_indices: Mapping[LocationCode, int] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Validate schedule topology and initialize immutable lookup indexes.

        Raises:
            DomainValidationError: If timestamps are not naive app-local
                datetimes, the schedule has too few stops, locations are
                duplicated, segment topology is mismatched, travel values are
                non-positive, or arrival times are inconsistent.
        """

        try:
            require_naive_datetime(self.departure_time, "departure_time")
            for index, stop in enumerate(self.stops):
                require_naive_datetime(stop.arrival_at, f"stops[{index}].arrival_at")
        except (TypeError, ValueError) as exc:
            raise DomainValidationError("Route schedule timestamps must be timezone-naive datetimes.") from exc

        if len(self.stops) < 2:
            raise DomainValidationError("A route schedule must contain at least two stops.")

        if len(self.segments) != len(self.stops) - 1:
            raise DomainValidationError("A route schedule must contain one segment between each pair of stops.")

        if self.stops[0].arrival_at != self.departure_time:
            raise DomainValidationError("The first stop arrival must equal the departure time.")

        arrival_times = {stop.location: stop.arrival_at for stop in self.stops}
        if len(arrival_times) != len(self.stops):
            raise DomainValidationError("A route schedule cannot contain duplicate locations.")

        for index, segment in enumerate(self.segments):
            current_stop = self.stops[index]
            next_stop = self.stops[index + 1]

            if segment.distance_km <= 0:
                raise DomainValidationError("Route segment distance must be positive.")

            if segment.duration <= timedelta(0):
                raise DomainValidationError("Route segment duration must be positive.")

            if segment.start != current_stop.location:
                raise DomainValidationError("Segment start does not match its scheduled stop.")

            if segment.end != next_stop.location:
                raise DomainValidationError("Segment end does not match its scheduled stop.")

            if current_stop.arrival_at + segment.duration != next_stop.arrival_at:
                raise DomainValidationError("Segment duration does not match scheduled arrival times.")

        object.__setattr__(self, "_arrival_times", MappingProxyType(arrival_times))
        object.__setattr__(
            self,
            "_stop_indices",
            MappingProxyType({stop.location: index for index, stop in enumerate(self.stops)}),
        )

    @property
    def eta_final(self) -> datetime:
        """Return the scheduled arrival time at the final route stop."""
        return self.stops[-1].arrival_at

    @property
    def total_distance_km(self) -> int:
        """Return the sum of all scheduled segment distances in kilometres."""
        return sum(segment.distance_km for segment in self.segments)

    def arrival_time_at(self, location: LocationCode) -> datetime:
        """Return the scheduled arrival time at a route location.

        Args:
            location: Location whose calculated arrival time is requested.

        Returns:
            Scheduled business-local arrival time.

        Raises:
            DomainValidationError: If the location is not part of the schedule.
        """
        try:
            return self._arrival_times[location]
        except KeyError:
            raise DomainValidationError(f"Location {location} is not part of this schedule.") from None

    def position_at(self, now: datetime) -> RoutePosition:
        """Return the route's temporal position at a business-local time.

        Args:
            now: Time at which route progress is evaluated.

        Returns:
            Position before departure, at a stop, in transit, or after arrival.

        Raises:
            DomainValidationError: If ``now`` is not a timezone-naive
                app-local datetime.
        """
        try:
            normalized_now = require_naive_datetime(now, "now")
        except (TypeError, ValueError) as exc:
            raise DomainValidationError("Route position time must be a timezone-naive datetime.") from exc

        first_city = self.stops[0].location
        first_departure = self._arrival_times[first_city]

        if normalized_now < first_departure:
            return RoutePosition(
                kind=RoutePositionKind.BEFORE_START, stop_city=first_city, next_eta=first_departure
            )

        for segment in self.segments:
            position = self._position_on_segment(segment, normalized_now, first_city)
            if position is not None:
                return position

        return self._position_after_segments(normalized_now, first_departure)

    def _position_on_segment(
        self,
        segment: RouteSegment,
        now: datetime,
        first_city: LocationCode,
    ) -> RoutePosition | None:
        """Return a position when ``now`` falls on the segment timeline.

        Args:
            segment: Segment being evaluated.
            now: Time at which route progress is evaluated.
            first_city: Departure location used for the departure boundary.

        Returns:
            Matching position, or ``None`` when ``now`` is outside the segment.
        """
        start_time = self._arrival_times[segment.start]
        end_time = self._arrival_times[segment.end]

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
        """Return the next scheduled stop time after ``city``, if one exists."""
        next_index = self._stop_indices[city] + 1
        if next_index >= len(self.stops):
            return None
        return self._arrival_times[self.stops[next_index].location]

    def _position_after_segments(self, now: datetime, first_departure: datetime) -> RoutePosition:
        """Return the fallback position after no segment matched ``now``."""
        return (
            RoutePosition(kind=RoutePositionKind.AFTER_END, stop_city=self.stops[-1].location)
            if now >= self._arrival_times[self.stops[-1].location]
            else RoutePosition(
                kind=RoutePositionKind.AT_STOP,
                stop_city=self.stops[0].location,
                next_eta=first_departure,
            )
        )
