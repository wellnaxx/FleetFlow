"""Use case for listing unassigned packages."""

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
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


class ViewUnassignedPackagesUseCase(AuthorizedUseCase[PageResult[DeliveryPackage]]):
    """List packages that are not assigned to any route."""

    def __init__(self, packages: PackageRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to query unassigned packages.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._packages = packages

    @requires(
        Permission.PACKAGE_VIEW_UNASSIGNED,
        operation=AuthorizationOperation.PACKAGE_LIST_UNASSIGNED,
        target_resource_type=AuditResourceType.PACKAGE,
        target_resource_id_resolver=None,
    )
    def execute(self, query: PageQuery = PageQuery()) -> PageResult[DeliveryPackage]:
        """Return all packages that are currently unassigned.

        Args:
            query: Pagination request. Defaults to a full uncounted list.

        Returns:
            Unassigned package page result.

        Raises:
            ValidationError: If pagination arguments are invalid.
        """
        return execute_page_query(
            query=query,
            list_all=self._packages.list_unassigned,
            list_page=lambda limit, offset: self._packages.list_unassigned_page(limit=limit, offset=offset),
            list_page_with_total=lambda limit, offset: self._packages.list_unassigned_page_with_total(
                limit=limit, offset=offset
            ),
        )
