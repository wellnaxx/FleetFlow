"""Pure domain calculations for package loads across route segments."""

from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.package_load import PackageLoad


class RouteLoadCalculator:
    """Calculate route cargo metrics from lightweight package-load values.

    The calculator is stateless and does not require delivery-package or route
    entities. Callers remain responsible for validating route topology and
    package weights before invoking it.
    """

    @staticmethod
    def maximum_segment_load(
        *,
        locations: tuple[LocationCode, ...],
        packages: tuple[PackageLoad, ...],
        extra_package: PackageLoad | None = None,
    ) -> float:
        """Return the heaviest cargo load carried on any route segment.

        Capacity is constrained by the maximum simultaneous load between two
        adjacent stops, not by the sum of every package assigned to the whole
        route. A package contributes its weight from its start-location index
        up to, but not including, its end-location index. Loads whose endpoints
        are absent from the route or occur in reverse order are ignored.

        ``extra_package`` is included in the calculation without changing the
        supplied package tuple. An empty route, a route without segments, or a
        route without applicable package loads produces ``0.0``.

        Args:
            locations: Ordered route locations used to identify segment spans.
            packages: Existing package loads associated with the route.
            extra_package: Optional candidate load evaluated alongside the
                existing packages without mutating them.

        Returns:
            Maximum simultaneous carried weight across adjacent route
            segments, or ``0.0`` when no segment has a package load.
        """
        indices = {location: index for index, location in enumerate(locations)}
        segment_loads = [0.0] * (len(locations) - 1)

        candidates = packages
        if extra_package is not None:
            candidates = (*candidates, extra_package)

        for package in candidates:
            start_index = indices.get(package.start_location)
            end_index = indices.get(package.end_location)

            if start_index is None or end_index is None or start_index >= end_index:
                continue

            for segment_index in range(start_index, end_index):
                segment_loads[segment_index] += package.weight

        return max(segment_loads, default=0.0)
