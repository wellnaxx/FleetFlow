"""Use case for listing all packages."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.ports.output.package_repository import PackageRepositoryPort


class ViewAllPackagesUseCase(AuthorizedUseCase[list[DeliveryPackage]]):
    """List all packages from the repository."""

    def __init__(self, packages: PackageRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to list packages.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._packages = packages

    @requires(Permission.PACKAGE_VIEW_ALL)
    def execute(self) -> list[DeliveryPackage]:
        """Return all persisted packages.

        Returns:
            Package entities currently stored in the repository.
        """
        return self._packages.list_all()
