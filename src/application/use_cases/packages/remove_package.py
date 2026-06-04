"""Use case for removing a package from runtime state."""

import logging

from src.application.exceptions.application_errors import NotFoundError
from src.application.services.authorization_service import AuthorizationService, requires_all
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.domain.exceptions import DomainConflictError, EntityNotFoundError
from src.ports.output.package_repository import PackageRepositoryPort

logger = logging.getLogger(__name__)


class RemovePackageUseCase(AuthorizedUseCase[DeliveryPackage]):
    """Remove a package from the repository and any assigned route."""

    def __init__(self, packages: PackageRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to fetch and remove packages.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._packages = packages

    @requires_all(Permission.PACKAGE_REMOVE, Permission.PACKAGE_VIEW)
    def execute(self, package_id: int) -> DeliveryPackage:
        """Remove a package by id.

        Args:
            package_id: Identifier of the package to remove.

        Returns:
            The removed package entity.

        Raises:
            PermissionError: If the caller lacks required package permissions.
            NotFoundError: If the package does not exist.
            DomainConflictError: If route-package assignment state is inconsistent.
            EntityNotFoundError: If customer-package ownership state is inconsistent.
        """
        package = self._get_package(package_id)
        self._detach_from_route(package)
        self._remove_from_customer(package)
        self._packages.remove(package_id)
        logger.info("Removed package %d.", package_id)
        return package

    def _get_package(self, package_id: int) -> DeliveryPackage:
        package = self._packages.get_by_id(package_id)
        if package is None:
            logger.warning("Package removal requested for missing package %d.", package_id)
            raise NotFoundError(f"Package with ID {package_id} not found.")
        return package

    def _detach_from_route(self, package: DeliveryPackage) -> None:
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
            package.route.detach_package(package)
        except EntityNotFoundError as exc:
            raise DomainConflictError(str(exc)) from exc

    def _remove_from_customer(self, package: DeliveryPackage) -> None:
        customer = getattr(package, "customer", None)
        if customer is None:
            logger.warning(
                "Package %d cannot be removed cleanly because customer is not hydrated.",
                package.package_id,
            )
            raise DomainConflictError(
                f"Package {package.package_id} has no hydrated customer."
            )

        try:
            customer.remove_package(package)
        except EntityNotFoundError as exc:
            raise DomainConflictError(str(exc)) from exc
