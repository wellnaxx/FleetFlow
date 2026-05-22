"""Output port for customer repository adapters."""

from typing import Protocol

from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo


class CustomerRepositoryPort(Protocol):
    """Persist and query customer aggregates."""

    def create(self, contact: ContactInfo) -> Customer:
        """Create and persist a customer aggregate.

        Args:
            contact: Validated customer contact information.

        Returns:
            Persisted customer with its allocated id.
        """
        ...

    def remove(self, customer_id: int) -> None:
        """Remove a customer by id.

        Args:
            customer_id: Customer id to remove.
        """
        ...

    def get_by_id(self, customer_id: int) -> Customer | None:
        """Return a customer by id, or `None` when absent.

        Args:
            customer_id: Customer id to look up.

        Returns:
            Matching customer, or `None`.
        """
        ...

    def get_by_email(self, email: str) -> Customer | None:
        """Return a customer by normalized email, or `None` when absent.

        Args:
            email: Normalized email address to look up.

        Returns:
            Matching customer, or `None`.
        """
        ...

    def get_by_phone(self, phone: str) -> Customer | None:
        """Return a customer by normalized phone number, or `None` when absent.

        Args:
            phone: Normalized phone number to look up.

        Returns:
            Matching customer, or `None`.
        """
        ...

    def list_by_name(self, name: str) -> list[Customer]:
        """Return customers matching a display name.

        Args:
            name: Display name to match.

        Returns:
            Customers matching the supplied name.
        """
        ...

    def list_all(self) -> list[Customer]:
        """Return all customers."""
        ...

    def list_page(self, limit: int, offset: int) -> list[Customer]:
        """Return a limited page of customers.

        Args:
            limit: Maximum number of customers to return.
            offset: Number of customers to skip.

        Returns:
            Customers in the requested page.
        """
        ...

    def list_page_with_total(self, limit: int, offset: int) -> tuple[list[Customer], int]:
        """Return a customer page and total count from one repository operation."""
        ...

    def count_all(self) -> int:
        """Return the total number of customers."""
        ...
