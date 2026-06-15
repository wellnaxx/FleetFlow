"""Use case for removing a package from runtime state."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.exceptions.application_errors import NotFoundError
from src.application.services.authorization_service import AuthorizationService, requires_all
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.events.package_events import PackageRemoved
from src.domain.exceptions import DomainConflictError, EntityNotFoundError
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.unit_of_work import UnitOfWorkPort

logger = logging.getLogger(__name__)


class RemovePackageUseCase(AuthorizedUseCase[DeliveryPackage]):
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

    @requires_all(Permission.PACKAGE_REMOVE, Permission.PACKAGE_VIEW)
    def execute(self, package_id: int) -> DeliveryPackage:
        """Remove a package by id.

        Args:
            package_id: Identifier of the package to remove.

        Returns:
            The removed package entity.

        Raises:
            PermissionError: If the caller lacks required package permissions.
            Exception: If the package removal persistence fails.
            NotFoundError: If the package does not exist.
            DomainConflictError: If route-package assignment state is inconsistent.
            EntityNotFoundError: If customer-package ownership state is inconsistent.
        """
        package = self._get_package(package_id)

        package_snapshot = package.snapshot_state()
        event_checkpoint = package.event_checkpoint()
        route = package.route
        customer = package.customer
        occurred_at = self._clock()

        try:
            self._detach_from_route(package, occurred_at=occurred_at)
            self._remove_from_customer(package)

            with self._unit_of_work as uow:
                uow.packages.remove(package_id)
                uow.commit()
        except Exception:
            logger.exception("Package removal did not complete successfully. Restoring package.")
            package.restore_state(package_snapshot)
            package.restore_event_checkpoint(event_checkpoint)

            if route is not None:
                route.restore_package_link(package)

            customer.restore_package_link(package)
            raise

        removed_event = PackageRemoved(  # noqa: F841 # pyright: ignore[reportUnusedVariable]
            package_id=package.package_id,
            customer_id=package.customer.customer_id,
            route_id=package_snapshot.route_id,
            occurred_at=occurred_at,
        )  # This will be used once outbox/publisher is implemented!

        logger.info("Removed package %d.", package_id)
        return package

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
