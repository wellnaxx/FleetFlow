from src.application.services.customer_service import CustomerService
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus
from src.domain.services.map import Map
from src.ports.output.package_repository import PackageRepositoryPort


class CreatePackageUseCase:
    def __init__(self, customers: CustomerService, packages: PackageRepositoryPort) -> None:
        self._customers = customers
        self._packages = packages


    def execute(
        self, start: str, end: str, weight: float, name: str, email: str = "", phone: str = ""
    ) -> DeliveryPackage:
        if not Map.is_valid_location(start):
            raise ValueError(f"Invalid start location: {start}")
        if not Map.is_valid_location(end):
            raise ValueError(f"Invalid end location: {end}")

        customer = self._customers.find_existing_customer(name, email, phone)
        if customer is None:
            customer = self._customers.create(name, email, phone)

        package_id = self._packages.next_id()

        package = DeliveryPackage(
            start_location=start, end_location=end, weight=weight, customer=customer, package_id=package_id
        )
        package.status = ItemStatus.TODO
        customer.add_package(package)
        self._packages.add(package)
        return package
