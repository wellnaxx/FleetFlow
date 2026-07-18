"""Domain service for calculating immutable route schedules."""

from datetime import datetime, timedelta
from itertools import pairwise

from src.domain.exceptions import DomainValidationError
from src.domain.services.map import Map
from src.domain.validation import require_positive_int
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.route_schedule import RouteSchedule, RouteSegment, ScheduledStop


class RouteScheduler:
    """Build route timing information from locations, map distances, and speed."""

    DEFAULT_SPEED_KMPH = 87

    @classmethod
    def build(
        cls,
        *,
        locations: tuple[LocationCode, ...],
        departure_time: datetime,
        speed_kmph: int = DEFAULT_SPEED_KMPH,
    ) -> RouteSchedule:
        """Calculate a route schedule without mutating an aggregate.

        Args:
            locations: Ordered route locations from departure to destination.
            departure_time: Business-local departure time from the first stop.
            speed_kmph: Constant travel speed used for every route segment.

        Returns:
            Immutable schedule containing ordered segments and stop times.

        Raises:
            DomainValidationError: If fewer than two locations are supplied,
                the speed is not positive, or the resulting schedule violates
                route schedule invariants.
            EntityNotFoundError: If the map has no distance for an adjacent
                pair of locations.
        """
        if len(locations) < 2:
            raise DomainValidationError("A route schedule requires at least two locations.")

        try:
            normalized_speed = require_positive_int(speed_kmph, "speed_kmph")
        except DomainValidationError as exc:
            raise DomainValidationError("Route speed must be a positive integer.") from exc

        stops: list[ScheduledStop] = [
            ScheduledStop(
                location=locations[0],
                arrival_at=departure_time,
            )
        ]
        segments: list[RouteSegment] = []
        current_time = departure_time

        for start, end in pairwise(locations):
            distance_km = Map.get_distance(start, end)
            duration = timedelta(hours=distance_km / normalized_speed)
            segments.append(RouteSegment(start, end, distance_km, duration))
            current_time += duration
            stops.append(ScheduledStop(end, current_time))

        return RouteSchedule(
            departure_time=departure_time,
            segments=tuple(segments),
            stops=tuple(stops),
        )
