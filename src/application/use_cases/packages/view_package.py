"""Use case for viewing one package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.exceptions.application_errors import NotFoundError
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission

if TYPE_CHECKING:
    from src.application.queries.packages.view_package import ViewPackageQuery
    from src.ports.output.package_repository import PackageRepositoryPort


def _resolve_package_target_id(
    _self: ViewPackageUseCase,
    query: ViewPackageQuery,
) -> int | None:
    """Resolve the audit target resource id for a package-view query."""
    return query.package_id


class ViewPackageUseCase(AuthorizedUseCase[DeliveryPackage]):
    """Retrieve one package through the published application query."""

    def __init__(self, packages: PackageRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to fetch packages.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._packages = packages

    @requires(
        Permission.PACKAGE_VIEW,
        operation=AuthorizationOperation.PACKAGE_VIEW,
        target_resource_type=AuditResourceType.PACKAGE,
        target_resource_id_resolver=_resolve_package_target_id,
    )
    def execute(self, query: ViewPackageQuery) -> DeliveryPackage:
        """Return one package by id.

        Args:
            query: Package lookup query containing the target identifier.

        Returns:
            The matching package entity.

        Raises:
            PermissionError: If the caller lacks package view permission.
            NotFoundError: If the package does not exist.
            DatabaseError: If package retrieval fails.
        """
        package_id = query.package_id
        package = self._packages.get_by_id(package_id)
        if not package:
            raise NotFoundError(f"Package with ID {package_id} not found.")
        return package
