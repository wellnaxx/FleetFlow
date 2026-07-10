"""Use case for assigning one or more packages to a route."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.exceptions.application_errors import NotFoundError
from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission
from src.domain.exceptions import DomainConflictError, DomainValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.ports.output.package_repository import PackageRepositoryPort
    from src.ports.output.route_repository import RouteRepositoryPort

logger = logging.getLogger(__name__)


def _resolve_route_target_id(
    _self: AssignPackagesToRouteUseCase,
    route_id: int,
    package_ids: list[int],  # noqa: ARG001
) -> int | None:
    """Resolve the audit target resource id for a package-assignment-to-route attempt."""
    return route_id


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

    @requires(
        Permission.ROUTE_ASSIGN_PACKAGE,
        operation=AuthorizationOperation.ROUTE_ASSIGN_PACKAGES,
        target_resource_type=AuditResourceType.ROUTE,
        target_resource_id_resolver=_resolve_route_target_id,
    )
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
        route = self._get_route(route_id)
        result = AssignPackagesToRouteResult(successes=[], errors=[])
        now = self._clock()

        for package_id in self._unique_package_ids(package_ids):
            package = self._packages.get_by_id(package_id)
            if package is None:
                result.errors.append(self._missing_package_error(package_id, route_id))
                continue

            if assignment_error := self._assigned_package_error(package):
                result.errors.append(assignment_error)
                continue

            try:
                result.successes.append(self._assign_package(route=route, package=package, now=now))
            except DomainConflictError as exc:
                logger.warning("Package assignment rejected for package %d: %s", package_id, exc)
                result.errors.append(PackageAssignmentError(package_id=package_id, message=str(exc)))

        logger.info(
            "Package assignment to route %d completed with %d success(es) and %d error(s).",
            route_id,
            len(result.successes),
            len(result.errors),
        )
        return result

    def _get_route(self, route_id: int) -> DeliveryRoute:
        route = self._routes.get_by_id(route_id)
        if route is None:
            logger.warning("Package assignment requested for missing route %d.", route_id)
            raise NotFoundError(f"Route with ID {route_id} not found.")
        return route

    def _unique_package_ids(self, package_ids: list[int]) -> list[int]:
        seen_package_ids: set[int] = set()
        unique_package_ids: list[int] = []

        for package_id in package_ids:
            if package_id in seen_package_ids:
                continue
            seen_package_ids.add(package_id)
            unique_package_ids.append(package_id)
        return unique_package_ids

    def _missing_package_error(self, package_id: int, route_id: int) -> PackageAssignmentError:
        logger.warning(
            "Package assignment skipped missing package %d for route %d.",
            package_id,
            route_id,
        )
        return PackageAssignmentError(package_id=package_id, message=f"Package {package_id} not found.")

    def _assigned_package_error(self, package: DeliveryPackage) -> PackageAssignmentError | None:
        if package.route_id is None:
            return None

        if package.route is None:
            message = f"Package {package.package_id} has route_id {package.route_id} but route is not hydrated."
        else:
            message = f"Package {package.package_id} is already on route {package.route_id}."

        logger.warning("Package assignment rejected for package %d: %s", package.package_id, message)
        return PackageAssignmentError(package_id=package.package_id, message=message)

    def _assign_package(
        self,
        route: DeliveryRoute,
        package: DeliveryPackage,
        now: datetime,
    ) -> PackageAssignmentSuccess:
        route_snapshot = route.snapshot_state()
        package_snapshot = package.snapshot_state()
        route_event_checkpoint = route.event_checkpoint()

        try:
            route.assign_package(package, now=now, occurred_at=now)
            self._packages.update_state(package)
        except DatabaseError:
            route.restore_state(route_snapshot)
            route.restore_event_checkpoint(route_event_checkpoint)
            package.restore_state(package_snapshot)
            raise

        return PackageAssignmentSuccess(
            package_id=package.package_id,
            route_id=route.route_id,
            eta_text=self._format_eta(route, package),
            route=route,
        )

    def _format_eta(self, route: DeliveryRoute, package: DeliveryPackage) -> str:
        if route.departure_time is None:
            return "N/A (route unscheduled)"

        try:
            eta_dt = route.arrival_time_at(package.end_location)
            return eta_dt.strftime("%Y-%m-%d %H:%M")
        except (DomainConflictError, DomainValidationError):
            return "N/A"
