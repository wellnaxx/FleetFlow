"""Use case for creating a delivery package."""

import logging

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.services.customer_service import CustomerService
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.auth import Permission
from src.domain.value_objects.location_code import LocationCode
from src.ports.output.package_repository import PackageRepositoryPort

logger = logging.getLogger(__name__)


class CreatePackageUseCase(AuthorizedUseCase[DeliveryPackage]):
    """Create a package and attach it to an existing or new customer."""

    def __init__(
        self, customers: CustomerService, packages: PackageRepositoryPort, authz: AuthorizationService
    ) -> None:
        """Initialize package creation dependencies.

        Args:
            customers: Service used to resolve or create customers.
            packages: Repository used to persist the new package.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._customers = customers
        self._packages = packages

    @requires(
        Permission.PACKAGE_CREATE,
        operation=AuthorizationOperation.PACKAGE_CREATE,
        target_resource_type=AuditResourceType.PACKAGE,
        target_resource_id_resolver=None,
    )
    def execute(
        self, start: str, end: str, weight: float, name: str, email: str = "", phone: str = ""
    ) -> DeliveryPackage:
        """Create and persist a delivery package.

        Args:
            start: Pickup location code.
            end: Delivery location code.
            weight: Package weight in kilograms.
            name: Customer name.
            email: Optional customer email address.
            phone: Optional customer phone number.

        Returns:
            The newly created delivery package.

        Raises:
            PermissionError: If the caller lacks package creation permission.
            DatabaseError: If customer or package persistence fails.
            DomainValidationError: If location code, delivery package, or contact information validation fails.
            ConflictError: If the supplied details point to conflicting customers or
                contradict the name on an existing customer.
            DomainConflictError: If the package is already linked to the customer.
            EntityNotFoundError: If package ownership transfer detects that the package is missing
                from the previous customer's active collection.
        """
        start_code = LocationCode(start)
        end_code = LocationCode(end)

        customer = self._customers.find_existing_customer(name, email, phone)
        if customer is None:
            customer = self._customers.create(name, email, phone)

        package = self._packages.create(
            start_location=start_code,
            end_location=end_code,
            weight=weight,
            customer=customer,
        )
        customer.add_package(package)
        logger.info(
            "Created package %d from %s to %s for customer %d.",
            package.package_id,
            package.start_location,
            package.end_location,
            customer.customer_id,
        )
        return package
