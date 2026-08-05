"""Query contract for browsing customers."""

from dataclasses import dataclass, field
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.application.use_cases.pagination import PageQuery, PageResult
from src.domain.entities.customer import Customer


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewAllCustomersQuery(Query):
    """Request customers using the shared pagination contract.

    Attributes:
        page: Optional limit, offset, and total-count selection.
    """

    page: PageQuery = field(default_factory=PageQuery)


VIEW_ALL_CUSTOMERS: Final[QueryKey[ViewAllCustomersQuery, PageResult[Customer]]] = QueryKey(
    name="view_all_customers",
    query_type=ViewAllCustomersQuery,
)
