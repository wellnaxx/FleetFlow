"""Query contract for retrieving one delivery route."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewRouteQuery(Query):
    """Request a delivery route by its persistent identifier.

    Attributes:
        route_id: Positive identifier of the route to retrieve.
    """

    route_id: int


VIEW_ROUTE: Final[QueryKey[ViewRouteQuery, DeliveryRoute]] = QueryKey(
    name="view_route",
    query_type=ViewRouteQuery,
)
