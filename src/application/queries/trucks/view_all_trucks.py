"""Query contract for listing the fleet's trucks."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.domain.entities.truck import Truck


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewAllTrucksQuery(Query):
    """Request every truck visible to the current principal.

    The query carries no selection fields because the existing workflow is an
    unpaginated complete listing.
    """


VIEW_ALL_TRUCKS: Final[QueryKey[ViewAllTrucksQuery, list[Truck]]] = QueryKey(
    name="view_all_trucks",
    query_type=ViewAllTrucksQuery,
)
