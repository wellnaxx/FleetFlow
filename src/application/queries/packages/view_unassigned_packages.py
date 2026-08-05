"""Query contract for browsing packages without a route assignment."""

from dataclasses import dataclass, field
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.application.use_cases.pagination import PageQuery, PageResult
from src.domain.entities.delivery_package import DeliveryPackage


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewUnassignedPackagesQuery(Query):
    """Request unassigned packages using the shared pagination contract.

    Attributes:
        page: Optional limit, offset, and total-count selection.
    """

    page: PageQuery = field(default_factory=PageQuery)


VIEW_UNASSIGNED_PACKAGES: Final[QueryKey[ViewUnassignedPackagesQuery, PageResult[DeliveryPackage]]] = QueryKey(
    name="view_unassigned_packages",
    query_type=ViewUnassignedPackagesQuery,
)
