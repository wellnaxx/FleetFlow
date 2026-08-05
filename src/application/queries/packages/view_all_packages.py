"""Query contract for browsing all packages."""

from dataclasses import dataclass, field
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.application.use_cases.pagination import PageQuery, PageResult
from src.domain.entities.delivery_package import DeliveryPackage


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewAllPackagesQuery(Query):
    """Request all packages using the shared pagination contract.

    Attributes:
        page: Optional limit, offset, and total-count selection.
    """

    page: PageQuery = field(default_factory=PageQuery)


VIEW_ALL_PACKAGES: Final[QueryKey[ViewAllPackagesQuery, PageResult[DeliveryPackage]]] = QueryKey(
    name="view_all_packages",
    query_type=ViewAllPackagesQuery,
)
