from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..value_objects.contact_info import ContactInfo  # noqa: TC001

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage


@dataclass
class Customer:
    contact: ContactInfo
    customer_id: int
    _delivery_packages: list[DeliveryPackage] = field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        repr=False,
    )

    @property
    def name(self) -> str:
        return self.contact.name

    @property
    def email(self) -> str:
        return self.contact.email

    @property
    def phone_number(self) -> str:
        return self.contact.phone_number

    @property
    def delivery_packages(self) -> tuple[DeliveryPackage, ...]:
        return tuple(self._delivery_packages)

    def add_package(self, package: DeliveryPackage) -> None:
        if package.customer is self:
            if any(p.package_id == package.package_id for p in self._delivery_packages):
                raise ValueError(f"Package with id {package.package_id} is already assigned to this customer.")
            self._delivery_packages.append(package)
            return

        old_customer = package.customer
        old_customer._remove_package_link(package)
        package.customer = self
        self._delivery_packages.append(package)


    def _remove_package_link(self, package: DeliveryPackage) -> None:
        for i, p in enumerate(self._delivery_packages):
            if p.package_id == package.package_id:
                self._delivery_packages.pop(i)
                return
        raise ValueError(f"Package with id {package.package_id} does not exist.")
