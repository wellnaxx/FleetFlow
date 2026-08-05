"""Query contract for package-to-route suitability searches."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage


@dataclass(frozen=True, slots=True, kw_only=True)
class FindSuitableRoutesForPackageQuery(Query):
    """Request routes capable of accepting a particular package.

    Attributes:
        package_id: Positive identifier of the package to evaluate.
    """

    package_id: int


FIND_SUITABLE_ROUTES_FOR_PACKAGE: Final[
    QueryKey[FindSuitableRoutesForPackageQuery, list[SuitableRouteForPackage]]
] = QueryKey(
    name="find_suitable_routes_for_package",
    query_type=FindSuitableRoutesForPackageQuery,
)
