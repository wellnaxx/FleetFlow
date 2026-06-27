from dataclasses import dataclass

from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True, slots=True)
class RemovePackageResult:
    package: DeliveryPackage
    customer: Customer
    route: DeliveryRoute | None
