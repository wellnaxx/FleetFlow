"""Use case for removing a package from runtime state."""

from src.application.services.authorization_service import AuthorizationService, requires_all
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.ports.output.package_repository import PackageRepositoryPort


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
            ValueError: If the package does not exist.
        """
        package = self._packages.get_by_id(package_id)
        if package is None:
            raise ValueError(f"Package with ID {package_id} not found")

        if package.route is not None:
            package.route.detach_package(package)

        package.customer.remove_package(package)
        self._packages.remove(package_id)
        return package
