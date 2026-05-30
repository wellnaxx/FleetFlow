"""Use case for assigning one or more packages to a route."""

from collections.abc import Callable
from datetime import datetime

from src.application.exceptions.application_errors import NotFoundError
from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.auth import Permission
from src.domain.exceptions import DomainConflictError, DomainValidationError
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort


class AssignPackagesToRouteUseCase(AuthorizedUseCase[AssignPackagesToRouteResult]):
    """Assign one or more packages to a route."""

    def __init__(
        self,
        routes: RouteRepositoryPort,
        packages: PackageRepositoryPort,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize assignment dependencies.

        Args:
            routes: Repository used to fetch the target route.
            packages: Repository used to fetch requested packages.
            authz: Service used for authorization checks.
            clock: Clock provider for assignment-time validation.
        """
        super().__init__(authz)
        self._routes = routes
        self._packages = packages
        self._clock = clock

    @requires(Permission.ROUTE_ASSIGN_PACKAGE)
    def execute(self, route_id: int, package_ids: list[int]) -> AssignPackagesToRouteResult:
        """Assign packages to the requested route.

        Args:
            route_id: Identifier of the target route.
            package_ids: Package ids to assign.

        Returns:
            A result object describing successful assignments and per-package
            failures.

        Raises:
            PermissionError: If the caller lacks package assignment permission.
            DatabaseError: If the package assignment persistence fails.
            NotFoundError: If the target route does not exist.
        """
        route = self._routes.get_by_id(route_id)
        if route is None:
            raise NotFoundError(f"Route with ID {route_id} not found.")

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

            if package.route_id is not None:
                if package.route is None:
                    message = f"Package {package_id} has route_id {package.route_id} but route is not hydrated."
                else:
                    message = f"Package {package_id} is already on route {package.route_id}."
                result.errors.append(
                    PackageAssignmentError(
                        package_id=package_id,
                        message=message,
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
            except DomainConflictError as exc:
                result.errors.append(PackageAssignmentError(package_id=package_id, message=str(exc)))

        return result

    def _format_eta(self, route: DeliveryRoute, package: DeliveryPackage) -> str:
        if route.departure_time is None:
            return "N/A (route unscheduled)"

        try:
            eta_dt = route.arrival_time_at(package.end_location)
            return eta_dt.strftime("%Y-%m-%d %H:%M")
        except (DomainConflictError, DomainValidationError):
            return "N/A"
