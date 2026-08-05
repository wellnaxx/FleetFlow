"""Query contract for retrieving one package."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.domain.entities.delivery_package import DeliveryPackage


@dataclass(frozen=True, slots=True, kw_only=True)
class ViewPackageQuery(Query):
    """Request a package by its persistent identifier.

    Attributes:
        package_id: Positive identifier of the package to retrieve.
    """

    package_id: int


VIEW_PACKAGE: Final[QueryKey[ViewPackageQuery, DeliveryPackage]] = QueryKey(
    name="view_package",
    query_type=ViewPackageQuery,
)
