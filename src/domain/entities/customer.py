"""Customer aggregate root and package ownership behavior."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin
from src.domain.events.customer_events import CustomerCreated
from src.domain.exceptions import DomainConflictError, EntityNotFoundError
from src.domain.validation import require_positive_int

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.events.base import DomainEvent
    from src.domain.value_objects.contact_info import ContactInfo


class Customer(DomainEventRecorderMixin):
    """Customer aggregate with contact details and active package ownership."""

    __slots__ = ("_customer_id", "_delivery_packages", "_pending_events", "contact")

    def __init__(self, contact: ContactInfo, customer_id: int) -> None:
        """Create a customer without recording a creation event.

        Direct construction is intended for persistence hydration. Use
        :meth:`create` when creating a new customer through a business
        workflow.

        Args:
            contact: Validated customer contact information.
            customer_id: Stable positive customer identifier.

        Raises:
            DomainValidationError: If ``customer_id`` is not a positive integer.
        """
        self.contact = contact
        self._customer_id = require_positive_int(customer_id, "customer_id")
        self._delivery_packages: list[DeliveryPackage] = []
        self._pending_events: list[DomainEvent] = []

    @property
    def customer_id(self) -> int:
        """Stable customer identifier."""
        return self._customer_id

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

    @classmethod
    def create(
        cls,
        contact: ContactInfo,
        customer_id: int,
        occurred_at: datetime | None = None,
    ) -> Customer:
        """Create a customer and record its creation event.

        Unlike direct construction, this factory records a `CustomerCreated`
        domain event. Persistence mappers should use the constructor when
        rehydrating existing customers.

        Args:
            contact: Validated customer contact information.
            customer_id: Unique positive customer identifier.
            occurred_at: Business time of creation. Defaults to the current time.

        Returns:
            Newly created customer with one pending `CustomerCreated` event.

        Raises:
            DomainValidationError: If ``customer_id`` is not a positive integer.
        """
        customer = cls(contact=contact, customer_id=customer_id)
        customer._record_event(
            CustomerCreated(
                occurred_at=occurred_at or datetime.now(),
                customer_id=customer.customer_id,
            )
        )
        return customer

    def add_package(self, package: DeliveryPackage) -> None:
        """Link a package to this customer, moving it from any previous customer.

        Args:
            package: Package to include in this customer's active collection.

        Raises:
            DomainConflictError: If the package is already linked to this customer.
            EntityNotFoundError: If the package is not in the old customer's active collection.
        """
        if package.customer.customer_id == self.customer_id:
            if package in self._delivery_packages:
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
        if package in self._delivery_packages:
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
        try:
            self._delivery_packages.remove(package)
        except ValueError:
            raise EntityNotFoundError(f"Package with id {package.package_id} does not exist.") from None
