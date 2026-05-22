"""Use case for listing unassigned packages."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.packages.pagination import validate_pagination
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
    def execute(self, limit: int | None = None, offset: int = 0) -> list[DeliveryPackage]:
        """Return all packages that are currently unassigned.

        Args:
            limit: Optional maximum number of packages to return.
            offset: Number of packages to skip when `limit` is provided.

        Returns:
            Packages without a route assignment.

        Raises:
            ValueError: If pagination arguments are invalid.
        """
        if not validate_pagination(limit, offset):
            return self._packages.list_unassigned()

        assert limit is not None
        return self._packages.list_unassigned_page(limit=limit, offset=offset)

    @requires(Permission.PACKAGE_VIEW_UNASSIGNED)
    def execute_with_count(self, limit: int, offset: int = 0) -> tuple[list[DeliveryPackage], int]:
        """Return an unassigned package page and total from one repository operation."""
        validate_pagination(limit, offset)
        return self._packages.list_unassigned_page_with_total(limit=limit, offset=offset)

    @requires(Permission.PACKAGE_VIEW_UNASSIGNED)
    def count(self) -> int:
        """Return the total number of unassigned packages."""
        return self._packages.count_unassigned()
