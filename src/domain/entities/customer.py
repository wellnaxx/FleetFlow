"""Customer aggregate root and package ownership behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.domain.exceptions import DomainConflictError, EntityNotFoundError
from src.domain.value_objects.contact_info import ContactInfo  # noqa: TC001

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage


@dataclass
class Customer:
    """Customer contact record with an active package collection."""

    contact: ContactInfo
    customer_id: int
    _delivery_packages: list[DeliveryPackage] = field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
        repr=False,
    )

    @property
    def name(self) -> str:
        """Customer display name."""
        return self.contact.name

    @property
    def email(self) -> str:
        """Normalized customer email address, or an empty string."""
        return self.contact.email

    @property
    def phone_number(self) -> str:
        """Normalized customer phone number, or an empty string."""
        return self.contact.phone_number

    @property
    def delivery_packages(self) -> tuple[DeliveryPackage, ...]:
        """Active packages currently linked to this customer."""
        return tuple(self._delivery_packages)

    def add_package(self, package: DeliveryPackage) -> None:
        """Link a package to this customer, moving it from any previous customer.

        Args:
            package: Package to include in this customer's active collection.

        Raises:
            DomainConflictError: If the package is already linked to this customer.
            EntityNotFoundError: If the package is not in the old customer's active collection.
        """
        if package.customer.customer_id == self.customer_id:
            if any(p.package_id == package.package_id for p in self._delivery_packages):
                raise DomainConflictError(
                    f"Package with id {package.package_id} is already assigned to this customer."
                )
            package.customer = self
            self._delivery_packages.append(package)
            return

        old_customer = package.customer
        old_customer.remove_package(package)
        package.customer = self
        self._delivery_packages.append(package)

    def restore_package_link(self, package: DeliveryPackage) -> None:
        """Restore a package-customer link while rebuilding persisted state.

        Args:
            package: Package to link to this customer.
        """
        if any(p.package_id == package.package_id for p in self._delivery_packages):
            return

        package.customer = self
        self._delivery_packages.append(package)

    def remove_package(self, package: DeliveryPackage) -> None:
        """Remove a package from this customer's active package collection.

        This does not clear package.customer. Removed packages keep their customer
        reference as historical ownership; this method only updates the customer's
        active package list.

        Args:
            package: Package to remove from the active collection.

        Raises:
            EntityNotFoundError: If the package is not in this customer's active collection.
        """
        for i, p in enumerate(self._delivery_packages):
            if p.package_id == package.package_id:
                self._delivery_packages.pop(i)
                return
        raise EntityNotFoundError(f"Package with id {package.package_id} does not exist.")
