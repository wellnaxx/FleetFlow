"""Use case for viewing one package."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.ports.output.package_repository import PackageRepositoryPort


class ViewPackageUseCase(AuthorizedUseCase[DeliveryPackage]):
    """Fetch one package by id."""

    def __init__(self, packages: PackageRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to fetch packages.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._packages = packages

    @requires(Permission.PACKAGE_VIEW)
    def execute(self, package_id: int) -> DeliveryPackage:
        """Return one package by id.

        Args:
            package_id: Identifier of the package to fetch.

        Returns:
            The matching package entity.

        Raises:
            ValueError: If the package does not exist.
        """
        package = self._packages.get_by_id(package_id)
        if not package:
            raise ValueError(f"Package with ID {package_id} not found")
        return package
