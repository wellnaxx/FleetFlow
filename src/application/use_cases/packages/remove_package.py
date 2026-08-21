"""Use case for removing a package from runtime state."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.exceptions.application_errors import NotFoundError
from src.application.results.remove_package_result import RemovePackageResult
from src.application.services.authorization_service import AuthorizationService, requires_all
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.exceptions import DomainConflictError, EntityNotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.application.commands.packages.remove_package import RemovePackageCommand
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.ports.output.package_repository import PackageRepositoryPort
    from src.ports.output.unit_of_work import UnitOfWorkPort

logger = logging.getLogger(__name__)


def _resolve_package_target_id(
    _self: RemovePackageUseCase,
    command: RemovePackageCommand,
) -> int | None:
    """Resolve the audit target resource id for a package-removal command."""
    return command.package_id


class RemovePackageUseCase(AuthorizedUseCase[RemovePackageResult]):
    """Remove a package from the repository and any assigned route."""

    def __init__(
        self,
        packages: PackageRepositoryPort,
        unit_of_work: UnitOfWorkPort,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to fetch and remove packages.
            unit_of_work: Transaction boundary used to persist package removal.
            authz: Service used for authorization checks.
            clock: Clock provider for package-removal events.
        """
        super().__init__(authz)
        self._packages = packages
        self._unit_of_work = unit_of_work
        self._clock = clock

    @requires_all(
        Permission.PACKAGE_REMOVE,
        Permission.PACKAGE_VIEW,
        operation=AuthorizationOperation.PACKAGE_REMOVE,
        target_resource_type=AuditResourceType.PACKAGE,
        target_resource_id_resolver=_resolve_package_target_id,
    )
    def execute(self, command: RemovePackageCommand) -> RemovePackageResult:
        """Remove a package by id.

        Args:
            command: Package-removal request containing the target identifier.

        Returns:
            Removal result containing the removed package, its customer, and
            the route it was detached from, if it had one.

        Raises:
            PermissionError: If the caller lacks required package permissions.
            Exception: If the package removal persistence fails.
            NotFoundError: If the package does not exist.
            DomainConflictError: If route-package assignment state is inconsistent.
            EntityNotFoundError: If customer-package ownership state is inconsistent.
        """
        package_id = command.package_id
        package = self._get_package(package_id)
        route = package.route
        customer = package.customer

        package_snapshot = package.snapshot_state()
        previous_location = package.current_location
        package_event_checkpoint = package.event_checkpoint()
        route_event_checkpoint = route.event_checkpoint() if route is not None else None
        occurred_at = self._clock()

        try:
            self._detach_from_route(package, occurred_at=occurred_at)
            self._remove_from_customer(package)
            package.record_removal(
                previous_route_id=package_snapshot.route_id,
                previous_status=package_snapshot.status,
                previous_location=previous_location,
                previous_expected_arrival=package_snapshot.expected_arrival,
                occurred_at=occurred_at,
            )

            with self._unit_of_work as uow:
                uow.packages.remove(package_id)
                uow.commit()
        except Exception:
            logger.exception("Package removal did not complete successfully. Restoring package.")
            package.restore_state(package_snapshot)
            package.restore_event_checkpoint(package_event_checkpoint)

            if route is not None:
                route.restore_package_link(package)

                if route_event_checkpoint is not None:
                    route.restore_event_checkpoint(route_event_checkpoint)

            customer.restore_package_link(package)
            raise

        logger.info("Removed package %d.", package_id)
        self.track_domain_recorder(package)
        self.track_domain_recorder(customer)
        if route is not None:
            self.track_domain_recorder(route)
        return RemovePackageResult(package, customer, route)

    def _get_package(self, package_id: int) -> DeliveryPackage:
        package = self._packages.get_by_id(package_id)
        if package is None:
            logger.warning("Package removal requested for missing package %d.", package_id)
            raise NotFoundError(f"Package with ID {package_id} not found.")
        return package

    def _detach_from_route(self, package: DeliveryPackage, *, occurred_at: datetime) -> None:
        if package.route_id is None:
            return

        if package.route is None:
            logger.warning(
                "Package %d cannot be removed cleanly because route %d is not hydrated.",
                package.package_id,
                package.route_id,
            )
            raise DomainConflictError(
                f"Package {package.package_id} is assigned to route {package.route_id}, "
                "but route is not hydrated."
            )

        try:
            package.route.detach_package(
                package,
                reason=PackageDetachmentReason.PACKAGE_REMOVED,
                occurred_at=occurred_at,
            )
        except EntityNotFoundError as exc:
            raise DomainConflictError(str(exc)) from exc

    def _remove_from_customer(self, package: DeliveryPackage) -> None:
        try:
            package.customer.remove_package(package)
        except EntityNotFoundError as exc:
            raise DomainConflictError(str(exc)) from exc
