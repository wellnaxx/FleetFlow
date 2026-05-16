"""Use case for finding routes that can carry a package."""

from collections.abc import Callable
from datetime import datetime

from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage
from src.application.services.authorization_service import AuthorizationService, requires_all
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort


def _sort_key(item: SuitableRouteForPackage) -> tuple[bool, datetime]:
    return (item.eta is None, item.eta or datetime.max)


class FindSuitableRoutesForPackageUseCase(AuthorizedUseCase[list[SuitableRouteForPackage]]):
    """Find candidate routes that can accept a package."""

    def __init__(
        self,
        routes: RouteRepositoryPort,
        packages: PackageRepositoryPort,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize route-search dependencies.

        Args:
            routes: Repository used to list candidate routes.
            packages: Repository used to fetch the target package.
            authz: Service used for authorization checks.
            clock: Clock provider for route acceptance checks.
        """
        super().__init__(authz)
        self._routes = routes
        self._packages = packages
        self._clock = clock

    @requires_all(Permission.PACKAGE_FIND_ROUTE_FOR, Permission.PACKAGE_VIEW, Permission.ROUTE_VIEW)
    def execute(self, package_id: int) -> list[SuitableRouteForPackage]:
        """Return suitable routes for a package ordered by ETA.

        Args:
            package_id: Identifier of the package to place.

        Returns:
            Candidate routes ordered by the best available ETA.

        Raises:
            ValueError: If the package does not exist.
        """
        package = self._packages.get_by_id(package_id)
        if package is None:
            raise ValueError(f"Package with ID {package_id} not found.")

        results: list[SuitableRouteForPackage] = []
        now = self._clock()

        for route in self._routes.list_all():
            if route.can_accept_package(package, now=now) is not None:
                continue

            capacity_left = None
            if route.truck is not None:
                capacity_left = route.truck.capacity - route.total_assigned_weight()

            try:
                eta = route.arrival_time_at(package.end_location)
            except ValueError:
                eta = None

            results.append(
                SuitableRouteForPackage(
                    route_id=route.route_id,
                    start_location=route.start_location,
                    end_location=route.end_location,
                    eta=eta,
                    capacity_left=capacity_left,
                    end_city=package.end_location,
                )
            )

        results.sort(key=_sort_key)
        return results
