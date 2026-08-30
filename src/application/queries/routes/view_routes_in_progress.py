"""Query contract for computing routes in progress at a business time."""

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.route_schedule import RoutePosition
from src.shared.validation import require_naive_datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewRoutesInProgressQuery(Query):
    """Request routes active at a supplied app-local business timestamp.

    Attributes:
        now: Naive app-local business time used to calculate every route's
            current position consistently for this query.
    """

    now: datetime

    def __post_init__(self) -> None:
        """Require a timezone-naive app-local evaluation timestamp."""
        require_naive_datetime(self.now, "now")


VIEW_ROUTES_IN_PROGRESS: Final[
    QueryKey[ViewRoutesInProgressQuery, list[tuple[DeliveryRoute, RoutePosition]]]
] = QueryKey(
    name="view_routes_in_progress",
    query_type=ViewRoutesInProgressQuery,
)
