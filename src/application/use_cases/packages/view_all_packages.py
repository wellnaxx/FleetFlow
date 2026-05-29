"""Use case for listing all packages."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.pagination import (
    PageQuery,
    PageResult,
    validate_page,
    validate_unpaginated_offset,
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
        if query.limit is None:
            validate_unpaginated_offset(query.offset)
            return PageResult(
                items=tuple(self._packages.list_all()),
                total=None,
                limit=None,
                offset=query.offset,
            )

        validate_page(query.limit, query.offset)
        if query.include_total:
            packages, total = self._packages.list_page_with_total(limit=query.limit, offset=query.offset)
        else:
            packages = self._packages.list_page(limit=query.limit, offset=query.offset)
            total = None

        return PageResult(
            items=tuple(packages),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
