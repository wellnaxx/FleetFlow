"""Use case for listing all packages."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.packages.pagination import validate_pagination
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
    def execute(self, limit: int | None = None, offset: int = 0) -> list[DeliveryPackage]:
        """Return all persisted packages.

        Args:
            limit: Optional maximum number of packages to return.
            offset: Number of packages to skip when `limit` is provided.

        Returns:
            Package entities currently stored in the repository.

        Raises:
            ValueError: If pagination arguments are invalid.
        """
        if not validate_pagination(limit, offset):
            return self._packages.list_all()

        assert limit is not None
        return self._packages.list_page(limit=limit, offset=offset)

    @requires(Permission.PACKAGE_VIEW_ALL)
    def execute_with_count(self, limit: int, offset: int = 0) -> tuple[list[DeliveryPackage], int]:
        """Return a package page and its total from one repository operation."""
        validate_pagination(limit, offset)
        return self._packages.list_page_with_total(limit=limit, offset=offset)

    @requires(Permission.PACKAGE_VIEW_ALL)
    def count(self) -> int:
        """Return the total number of persisted packages."""
        return self._packages.count_all()
