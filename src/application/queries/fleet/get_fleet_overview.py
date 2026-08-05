"""Query contract for the point-in-time fleet overview."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.application.results.fleet_overview import FleetOverview


@dataclass(frozen=True, slots=True, kw_only=True)
class GetFleetOverviewQuery(Query):
    """Request the current cross-aggregate fleet projection.

    The handler's use case obtains the generation time from its injected
    clock, ensuring callers cannot choose the business timestamp used by the
    projection.

    Attributes:
        active_route_limit: Maximum number of ETA-ordered active routes to
            include. Application validation requires a value from 1 to 100.
    """

    active_route_limit: int = 10


GET_FLEET_OVERVIEW: Final[QueryKey[GetFleetOverviewQuery, FleetOverview]] = QueryKey(
    name="get_fleet_overview",
    query_type=GetFleetOverviewQuery,
)
