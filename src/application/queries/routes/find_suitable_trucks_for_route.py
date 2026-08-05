"""Query contract for route-to-truck suitability searches."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.domain.entities.truck import Truck


@dataclass(frozen=True, slots=True, kw_only=True)
class FindSuitableTrucksForRouteQuery(Query):
    """Request trucks capable of serving a particular route.

    Attributes:
        route_id: Positive identifier of the route to evaluate.
    """

    route_id: int


FIND_SUITABLE_TRUCKS_FOR_ROUTE: Final[QueryKey[FindSuitableTrucksForRouteQuery, list[Truck]]] = QueryKey(
    name="find_suitable_trucks_for_route",
    query_type=FindSuitableTrucksForRouteQuery,
)
