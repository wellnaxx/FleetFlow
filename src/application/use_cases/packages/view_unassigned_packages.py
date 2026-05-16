"""Use case for listing unassigned packages."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.ports.output.package_repository import PackageRepositoryPort


class ViewUnassignedPackagesUseCase(AuthorizedUseCase[list[DeliveryPackage]]):
    """List packages that are not assigned to any route."""

    def __init__(self, packages: PackageRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to query unassigned packages.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._packages = packages

    @requires(Permission.PACKAGE_VIEW_UNASSIGNED)
    def execute(self) -> list[DeliveryPackage]:
        """Return all packages that are currently unassigned.

        Returns:
            Packages without a route assignment.
        """
        return self._packages.list_unassigned()
