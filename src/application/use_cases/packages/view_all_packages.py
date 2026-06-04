"""Use case for listing all packages."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.pagination import (
    PageQuery,
    PageResult,
    execute_page_query,
)
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.ports.output.package_repository import PackageRepositoryPort


class ViewAllPackagesUseCase(AuthorizedUseCase[PageResult[DeliveryPackage]]):
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
    def execute(self, query: PageQuery = PageQuery()) -> PageResult[DeliveryPackage]:
        """Return all persisted packages.

        Args:
            query: Pagination request. Defaults to a full uncounted list.

        Returns:
            Package page result.

        Raises:
            ValidationError: If pagination arguments are invalid.
        """
        return execute_page_query(
            query=query,
            list_all=self._packages.list_all,
            list_page=lambda limit, offset: self._packages.list_page(limit=limit, offset=offset),
            list_page_with_total=lambda limit, offset: self._packages.list_page_with_total(
                limit=limit, offset=offset
            ),
        )
