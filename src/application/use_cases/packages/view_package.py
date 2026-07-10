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
    from src.ports.output.package_repository import PackageRepositoryPort


def _resolve_package_target_id(
    _self: ViewPackageUseCase,
    package_id: int,
) -> int | None:
    """Resolve the audit target resource id for a package view attempt."""
    return package_id


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

    @requires(
        Permission.PACKAGE_VIEW,
        operation=AuthorizationOperation.PACKAGE_VIEW,
        target_resource_type=AuditResourceType.PACKAGE,
        target_resource_id_resolver=_resolve_package_target_id,
    )
    def execute(self, package_id: int) -> DeliveryPackage:
        """Return one package by id.

        Args:
            package_id: Identifier of the package to fetch.

        Returns:
            The matching package entity.

        Raises:
            PermissionError: If the caller lacks package view permission.
            NotFoundError: If the package does not exist.
        """
        package = self._packages.get_by_id(package_id)
        if not package:
            raise NotFoundError(f"Package with ID {package_id} not found.")
        return package
