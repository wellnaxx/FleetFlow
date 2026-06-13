from src.adapters.driven.persistence.database.executor import (
    execute_insert,
    execute_write,
    fetch_all,
    fetch_one,
)
from src.adapters.driven.persistence.database.mappers.customer import map_customer
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo


class PostgresCustomerRepository:
    """Postgres-backed customer repository implementation."""

    def create(self, contact: ContactInfo) -> Customer:
        """Create and persist a customer.

        Args:
            contact: Validated customer contact information.

        Returns:
            Persisted customer with its database-allocated id.

        Raises:
            DatabaseError: If the insert fails or does not return an id.
            ValueError: If persisted contact data is invalid.
        """
        customer_id = execute_insert(QUERIES.customers.add, (contact.name, contact.email, contact.phone_number))

        return Customer.create(customer_id=customer_id, contact=contact)

    def remove(self, customer_id: int) -> None:
        """Remove a customer by id.

        Args:
            customer_id: Customer id to remove.

        Returns:
            None.

        Raises:
            DatabaseError: If the delete operation fails.
        """
        execute_write(QUERIES.customers.remove, (customer_id,))

    def get_by_id(self, customer_id: int) -> Customer | None:
        """Return a customer by id.

        Args:
            customer_id: Customer id to look up.

        Returns:
            Matching customer, or `None` when no row exists.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required customer column is missing.
            TypeError: If a required customer column has an unexpected type.
            ValueError: If persisted contact data is invalid.
        """
        customer_row = fetch_one(QUERIES.customers.get_by_id, (customer_id,))
        if customer_row is None:
            return None

        return map_customer(customer_row)

    def get_by_email(self, email: str) -> Customer | None:
        """Return a customer by normalized email address.

        Args:
            email: Normalized email address to look up.

        Returns:
            Matching customer, or `None` when no row exists.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required customer column is missing.
            TypeError: If a required customer column has an unexpected type.
            ValueError: If persisted contact data is invalid.
        """
        customer_row = fetch_one(QUERIES.customers.get_by_email, (email,))
        if customer_row is None:
            return None

        return map_customer(customer_row)

    def get_by_phone(self, phone: str) -> Customer | None:
        """Return a customer by normalized phone number.

        Args:
            phone: Normalized phone number to look up.

        Returns:
            Matching customer, or `None` when no row exists.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required customer column is missing.
            TypeError: If a required customer column has an unexpected type.
            ValueError: If persisted contact data is invalid.
        """
        customer_row = fetch_one(QUERIES.customers.get_by_phone, (phone,))
        if customer_row is None:
            return None

        return map_customer(customer_row)

    def list_by_name(self, name: str) -> list[Customer]:
        """Return customers whose normalized names match the input.

        Args:
            name: Customer display name to match case-insensitively.

        Returns:
            Customers with the same normalized name.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required customer column is missing.
            TypeError: If a required customer column has an unexpected type.
            ValueError: If persisted contact data is invalid.
        """
        normalized_name = name.strip().casefold()
        customer_rows = fetch_all(QUERIES.customers.list_by_name, (normalized_name,))
        return [map_customer(customer_row) for customer_row in customer_rows]

    def list_all(self) -> list[Customer]:
        """Return all customers.

        Returns:
            All persisted customers.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required customer column is missing.
            TypeError: If a required customer column has an unexpected type.
            ValueError: If persisted contact data is invalid.
        """
        customer_rows = fetch_all(QUERIES.customers.list_all)
        return [map_customer(customer_row) for customer_row in customer_rows]

    def list_page(self, limit: int, offset: int) -> list[Customer]:
        """Return a limited page of customers.

        Args:
            limit: Maximum number of customers to return.
            offset: Number of customers to skip.

        Returns:
            Customers in the requested page.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required customer column is missing.
            TypeError: If a required customer column has an unexpected type.
            ValueError: If persisted contact data is invalid.
        """
        customer_rows = fetch_all(QUERIES.customers.list_page, (limit, offset))
        return [map_customer(customer_row) for customer_row in customer_rows]

    def list_page_with_total(self, limit: int, offset: int) -> tuple[list[Customer], int]:
        """Return a customer page and total count from one database query."""
        rows = fetch_all(QUERIES.customers.list_page_with_total, (limit, offset))
        if not rows:
            return [], 0

        total = rows[0]["total"]
        if not isinstance(total, int) or isinstance(total, bool):
            raise TypeError("Customer count must be an integer.")

        customer_rows = [row for row in rows if row["customer_id"] is not None]
        return [map_customer(customer_row) for customer_row in customer_rows], total

    def count_all(self) -> int:
        """Return the total number of customers.

        Returns:
            Total persisted customer count.

        Raises:
            DatabaseError: If the count query fails.
            KeyError: If the count column is missing.
            TypeError: If the count column has an unexpected type.
        """
        row = fetch_one(QUERIES.customers.count_all)
        if row is None:
            return 0

        total = row["total"]
        if not isinstance(total, int) or isinstance(total, bool):
            raise TypeError("Customer count must be an integer.")
        return total
