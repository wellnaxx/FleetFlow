"""Use case for listing unassigned packages."""

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.queries.packages.view_unassigned_packages import ViewUnassignedPackagesQuery
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.pagination import (
    PageResult,
    execute_page_query,
)
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.ports.output.package_repository import PackageRepositoryPort


class ViewUnassignedPackagesUseCase(AuthorizedUseCase[PageResult[DeliveryPackage]]):
    """Browse unassigned packages through the published query contract.

    Command-line and HTTP adapters dispatch the same typed query. The use case
    owns authorization and pagination selection, while the repository owns
    persistence-specific listing operations.
    """

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
    def execute(self, query: ViewUnassignedPackagesQuery) -> PageResult[DeliveryPackage]:
        """Return all packages that are currently unassigned.

        Args:
            query: Unassigned-package query containing pagination and
                total-count selection.

        Returns:
            Unassigned package page result.

        Raises:
            PermissionError: If the caller lacks unassigned-package viewing
                permission.
            ValidationError: If pagination arguments are invalid.
            DatabaseError: If package retrieval fails.
        """
        return execute_page_query(
            query=query.page,
            list_all=self._packages.list_unassigned,
            list_page=lambda limit, offset: self._packages.list_unassigned_page(limit=limit, offset=offset),
            list_page_with_total=lambda limit, offset: self._packages.list_unassigned_page_with_total(
                limit=limit, offset=offset
            ),
        )
