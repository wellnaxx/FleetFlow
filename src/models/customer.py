from __future__ import annotations
from .contact_info import ContactInfo
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar
if TYPE_CHECKING:
    from models.delivery_package import DeliveryPackage

@dataclass
class Customer:
    contact: ContactInfo
    customer_id: int | None = None
    _delivery_packages: list[DeliveryPackage] = field(default_factory=list, repr=False)
    

    _next_id: ClassVar[int] = 1

    def __post_init__(self):
        if self.customer_id is None:
            self.customer_id = type(self)._next_id
            type(self)._next_id += 1

    @property
    def name(self) -> str:  return self.contact.name
    @property
    def email(self) -> str: return self.contact.email
    @property
    def phone_number(self) -> str: return self.contact.phone_number

    @property
    def delivery_packages(self) -> tuple[DeliveryPackage, ...]:
        return tuple(self._delivery_packages)

    def add_package(self, package: DeliveryPackage) -> None:
        if package.customer is not self:
            if package.customer is not None:
                package.customer.remove_package(package)
            package.customer = self
        if any(p.package_id == package.package_id for p in self._delivery_packages):
            raise ValueError(f"Package with id {package.package_id} is already assigned to this customer.")
        self._delivery_packages.append(package)

    def remove_package(self, package: DeliveryPackage):
        for i, p in enumerate(self._delivery_packages):
            if p.package_id == package.package_id:
                self._delivery_packages.pop(i)
                if package.customer is self:
                    package.customer = None
                return
        raise ValueError(f"Package with id {package.package_id} does not exist.")
