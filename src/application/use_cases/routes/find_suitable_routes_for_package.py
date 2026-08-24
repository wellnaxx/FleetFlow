"""Use case for finding routes that can carry a package."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.exceptions.application_errors import NotFoundError
from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage
from src.application.services.authorization_service import AuthorizationService, requires_all
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission
from src.domain.exceptions import DomainConflictError, DomainValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.application.queries.routes.find_suitable_routes_for_package import (
        FindSuitableRoutesForPackageQuery,
    )
    from src.ports.output.package_repository import PackageRepositoryPort
    from src.ports.output.route_repository import RouteRepositoryPort


def _sort_key(item: SuitableRouteForPackage) -> tuple[bool, datetime]:
    return (item.eta is None, item.eta or datetime.max)


def _resolve_package_target_id(
    _self: FindSuitableRoutesForPackageUseCase,
    query: FindSuitableRoutesForPackageQuery,
) -> int | None:
    """Resolve the audit target resource id for a find-suitable-routes-for-package attempt."""
    return query.package_id


class FindSuitableRoutesForPackageUseCase(AuthorizedUseCase[list[SuitableRouteForPackage]]):
    """Find suitable routes through the published application query contract."""

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

    @requires_all(
        Permission.PACKAGE_FIND_ROUTE_FOR,
        Permission.PACKAGE_VIEW,
        Permission.ROUTE_VIEW,
        operation=AuthorizationOperation.PACKAGE_FIND_SUITABLE_ROUTES,
        target_resource_type=AuditResourceType.PACKAGE,
        target_resource_id_resolver=_resolve_package_target_id,
    )
    def execute(self, query: FindSuitableRoutesForPackageQuery) -> list[SuitableRouteForPackage]:
        """Return suitable routes for a package ordered by ETA.

        Args:
            query: Package identifier to evaluate against available routes.

        Returns:
            Candidate routes ordered by the best available ETA.

        Raises:
            PermissionError: If the caller lacks required package or route permissions.
            NotFoundError: If the package does not exist.
            DatabaseError: If package or route retrieval fails.
        """
        package_id = query.package_id
        package = self._packages.get_by_id(package_id)
        if package is None:
            raise NotFoundError(f"Package with ID {package_id} not found.")

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
            except (DomainConflictError, DomainValidationError):
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
