"""Query contract for browsing all delivery routes."""

from dataclasses import dataclass, field
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.application.use_cases.pagination import PageQuery, PageResult
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewAllRoutesQuery(Query):
    """Request routes using the shared pagination contract.

    Attributes:
        page: Optional limit, offset, and total-count selection.
    """

    page: PageQuery = field(default_factory=PageQuery)


VIEW_ALL_ROUTES: Final[QueryKey[ViewAllRoutesQuery, PageResult[DeliveryRoute]]] = QueryKey(
    name="view_all_routes",
    query_type=ViewAllRoutesQuery,
)
