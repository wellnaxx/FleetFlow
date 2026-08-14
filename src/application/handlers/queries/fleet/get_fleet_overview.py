"""Query handler for the cross-aggregate fleet overview."""

from src.application.queries.fleet.get_fleet_overview import GetFleetOverviewQuery
from src.application.results.fleet_overview import FleetOverview
from src.application.use_cases.fleet.get_overview import GetFleetOverviewUseCase


class GetFleetOverviewQueryHandler:
    """Adapt a fleet-overview query to the point-in-time workflow."""

    def __init__(self, use_case: GetFleetOverviewUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized fleet-overview workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: GetFleetOverviewQuery) -> FleetOverview:
        """Return the current fleet projection with a bounded active set.

        Args:
            query: Maximum active-route selection requested by the caller.

        Returns:
            Point-in-time fleet overview produced by the use case.

        Raises:
            Exception: Propagates authorization, validation, persistence, and
                other failures raised by the use case.
        """
        return self._use_case.execute(query.active_route_limit)
