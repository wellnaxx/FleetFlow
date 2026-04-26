"""Use case for creating a delivery package."""

from src.application.services.customer_service import CustomerService
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus
from src.domain.services.map import Map
from src.ports.output.package_repository import PackageRepositoryPort


class CreatePackageUseCase:
    """Create a package and attach it to an existing or new customer."""

    def __init__(self, customers: CustomerService, packages: PackageRepositoryPort) -> None:
        """Initialize package creation dependencies.

        Args:
            customers: Service used to resolve or create customers.
            packages: Repository used to persist the new package.
        """
        self._customers = customers
        self._packages = packages

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
            ValueError: If a location is invalid or customer resolution fails.
        """
        if not Map.is_valid_location(start):
            raise ValueError(f"Invalid start location: {start}")
        if not Map.is_valid_location(end):
            raise ValueError(f"Invalid end location: {end}")

        customer = self._customers.find_existing_customer(name, email, phone)
        if customer is None:
            customer = self._customers.create(name, email, phone)

        package_id = self._packages.peek_next_id()

        package = DeliveryPackage(
            start_location=start, end_location=end, weight=weight, customer=customer, package_id=package_id
        )
        package.status = ItemStatus.TODO
        customer.add_package(package)
        self._packages.add(package)
        return package
