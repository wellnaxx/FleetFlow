"""Query handler for package-to-route suitability searches."""

from src.application.queries.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageQuery,
)
from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage
from src.application.use_cases.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageUseCase,
)


class FindSuitableRoutesForPackageQueryHandler:
    """Adapt a package identifier to the route-suitability workflow."""

    def __init__(self, use_case: FindSuitableRoutesForPackageUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized route-suitability workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, query: FindSuitableRoutesForPackageQuery) -> list[SuitableRouteForPackage]:
        """Return routes suitable for the identified package.

        Args:
            query: Identifier of the package to evaluate.

        Returns:
            Ordered suitability projections produced by the use case.

        Raises:
            Exception: Propagates authorization, lookup, domain, persistence,
                and other failures raised by the use case.
        """
        return self._use_case.execute(query.package_id)
