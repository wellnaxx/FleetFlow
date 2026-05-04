"""Use case for assigning one or more packages to a route."""

from collections.abc import Callable
from datetime import datetime

from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort


class AssignPackagesToRouteUseCase:
    """Assign one or more packages to a route."""

    def __init__(
        self,
        routes: RouteRepositoryPort,
        packages: PackageRepositoryPort,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize assignment dependencies.

        Args:
            routes: Repository used to fetch the target route.
            packages: Repository used to fetch requested packages.
            clock: Clock provider for assignment-time validation.
        """
        self._routes = routes
        self._packages = packages
        self._clock = clock

    def execute(self, route_id: int, package_ids: list[int]) -> AssignPackagesToRouteResult:
        """Assign packages to the requested route.

        Args:
            route_id: Identifier of the target route.
            package_ids: Package ids to assign.

        Returns:
            A result object describing successful assignments and per-package
            failures.

        Raises:
            ValueError: If the target route does not exist.
        """
        route = self._routes.get_by_id(route_id)
        if route is None:
            raise ValueError(f"Route with ID {route_id} not found.")

        result = AssignPackagesToRouteResult(successes=[], errors=[])
        seen_package_ids: set[int] = set()
        now = self._clock()

        for package_id in package_ids:
            if package_id in seen_package_ids:
                continue
            seen_package_ids.add(package_id)

            package = self._packages.get_by_id(package_id)
            if package is None:
                result.errors.append(
                    PackageAssignmentError(package_id=package_id, message=f"Package {package_id} not found.")
                )
                continue

            if package.route is not None:
                result.errors.append(
                    PackageAssignmentError(
                        package_id=package_id,
                        message=f"Package {package_id} is already on route {package.route.route_id}.",
                    )
                )
                continue

            try:
                route.assign_package(package, now=now)
                self._packages.update_state(package)
                result.successes.append(
                    PackageAssignmentSuccess(
                        package_id=package.package_id,
                        route_id=route.route_id,
                        eta_text=self._format_eta(route, package),
                    )
                )
            except ValueError as exc:
                result.errors.append(PackageAssignmentError(package_id=package_id, message=str(exc)))

        return result

    def _format_eta(self, route: DeliveryRoute, package: DeliveryPackage) -> str:
        if route.departure_time is None:
            return "N/A (route unscheduled)"

        try:
            eta_dt = route.arrival_time_at(package.end_location)
            return eta_dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return "N/A"
