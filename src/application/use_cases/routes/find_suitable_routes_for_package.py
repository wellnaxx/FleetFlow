from collections.abc import Callable
from datetime import datetime

from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort


def _sort_key(item: SuitableRouteForPackage) -> tuple[bool, datetime]:
    return (item.eta is None, item.eta or datetime.max)


class FindSuitableRoutesForPackageUseCase:
    """Find candidate routes that can accept a package."""

    def __init__(
        self,
        routes: RouteRepositoryPort,
        packages: PackageRepositoryPort,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._routes = routes
        self._packages = packages
        self._clock = clock

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
