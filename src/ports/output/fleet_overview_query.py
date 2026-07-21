"""Output port for retrieving a point-in-time fleet overview projection."""

from datetime import datetime
from typing import Protocol

from src.application.results.fleet_overview import FleetOverview


class FleetOverviewQueryPort(Protocol):
    """Build read-only operational summaries from the active persistence backend."""

    def get_overview(
        self,
        *,
        generated_at: datetime,
        active_route_limit: int,
    ) -> FleetOverview:
        """Return a coherent fleet snapshot evaluated at one business time.

        ``generated_at`` is both the temporal cutoff for past-due metrics and
        route-position calculations and the timestamp stored on the returned
        projection. Implementations must use that value consistently rather
        than obtaining their own current time.

        Args:
            generated_at: App-local business time at which state is evaluated.
            active_route_limit: Maximum active-route projections to return.
                Callers must supply a value from 1 through 100.

        Returns:
            Fleet counts and ordered active-route projections from one coherent
            persistence snapshot.

        Raises:
            TypeError: If ``active_route_limit`` has an invalid runtime type.
            ValueError: If ``active_route_limit`` is outside the supported
                range or persisted aggregate data violates the result contract.
            RuntimeError: If an active route position lacks fields required by
                its position kind.
        """
        ...
