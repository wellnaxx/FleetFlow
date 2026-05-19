"""In-memory customer repository implementation."""

from collections.abc import Mapping

from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo


class InMemoryCustomerRepository:
    """In-memory customer repository.

    Normal customer creation allocates ids inside `create()`. Snapshot restore
    and memory-only tests may still use `add()` to load an existing customer id.
    """

    def __init__(self) -> None:
        """Initialize an empty customer repository."""
        self._customers_by_id: dict[int, Customer] = {}
        self._id_by_email: dict[str, int] = {}
        self._id_by_phone: dict[str, int] = {}
        self._next_id: int = 1

    def peek_next_id(self) -> int:
        """Return the next memory id counter.

        This is intentionally not part of the shared customer repository port;
        it exists for in-memory world-state snapshots.

        Returns:
            The current next id counter.
        """
        return self._next_id

    def create(self, contact: ContactInfo) -> Customer:
        """Create and store a customer with an in-memory allocated id.

        Args:
            contact: Validated customer contact information.

        Returns:
            Stored customer with its allocated id.
        """
        customer = Customer(customer_id=self._next_id, contact=contact)
        self.add(customer)
        return customer

    def add(self, customer: Customer) -> Customer:
        """Add an existing customer and advance the memory id counter.

        Args:
            customer: Customer entity to store.

        Raises:
            ValueError: If a customer with the same id already exists.
        """
        if customer.customer_id in self._customers_by_id:
            raise ValueError(f"Customer with id {customer.customer_id} already exists.")
        if customer.email:
            existing_id = self._id_by_email.get(customer.email)
            if existing_id is not None and existing_id != customer.customer_id:
                raise ValueError(f"Email already in use by customer id={existing_id}")
        if customer.phone_number:
            existing_id = self._id_by_phone.get(customer.phone_number)
            if existing_id is not None and existing_id != customer.customer_id:
                raise ValueError(f"Phone already in use by customer id={existing_id}")
        self._customers_by_id[customer.customer_id] = customer
        if customer.email:
            self._id_by_email[customer.email] = customer.customer_id
        if customer.phone_number:
            self._id_by_phone[customer.phone_number] = customer.customer_id

        self._next_id = max(self._next_id, customer.customer_id + 1)
        return customer

    def remove(self, customer_id: int) -> None:
        """Remove a customer and any email/phone indexes for that record.

        Args:
            customer_id: Customer id to remove.
        """
        customer = self._customers_by_id.get(customer_id)
        if customer is None:
            return

        if customer.email:
            self._id_by_email.pop(customer.email, None)

        if customer.phone_number:
            self._id_by_phone.pop(customer.phone_number, None)

        self._customers_by_id.pop(customer_id, None)

    def get_by_id(self, customer_id: int) -> Customer | None:
        """Return a customer by id, if present.

        Args:
            customer_id: Customer id to look up.

        Returns:
            Matching customer, or `None`.
        """
        return self._customers_by_id.get(customer_id, None)

    def get_by_email(self, email: str) -> Customer | None:
        """Return a customer by email, if present.

        Args:
            email: Normalized email address to look up.

        Returns:
            Matching customer, or `None`.
        """
        customer_id = self._id_by_email.get(email, None)
        if customer_id is None:
            return None
        return self._customers_by_id[customer_id]

    def get_by_phone(self, phone: str) -> Customer | None:
        """Return a customer by phone number, if present.

        Args:
            phone: Normalized phone number to look up.

        Returns:
            Matching customer, or `None`.
        """
        customer_id = self._id_by_phone.get(phone, None)
        if customer_id is None:
            return None
        return self._customers_by_id[customer_id]

    def list_by_name(self, name: str) -> list[Customer]:
        """Return customers whose normalized names match the input.

        Args:
            name: Name to match case-insensitively.

        Returns:
            Customers with the same normalized name.
        """
        return [
            customer
            for customer in self.list_all()
            if (customer.name or "").strip().casefold() == (name or "").strip().casefold()
        ]

    def list_all(self) -> list[Customer]:
        """Return all customers ordered by id."""
        return [self._customers_by_id[customer_id] for customer_id in sorted(self._customers_by_id)]

    def list_page(self, limit: int, offset: int) -> list[Customer]:
        """Return a page of customers ordered by id.

        Args:
            limit: Maximum number of customers to return.
            offset: Number of customers to skip.

        Returns:
            Customers in the requested page.
        """
        return self.list_all()[offset : offset + limit]

    def count_all(self) -> int:
        """Return the total number of customers."""
        return len(self._customers_by_id)

    def replace_customers(self, customers_by_id: Mapping[int, Customer], next_id: int) -> None:
        """Replace the full customer state from a snapshot load.

        Args:
            customers_by_id: Replacement customers keyed by id.
            next_id: Next customer id counter to restore.
        """
        self._customers_by_id = dict(customers_by_id)
        self._id_by_email = {
            customer.email: customer.customer_id for customer in customers_by_id.values() if customer.email
        }
        self._id_by_phone = {
            customer.phone_number: customer.customer_id
            for customer in customers_by_id.values()
            if customer.phone_number
        }
        self._next_id = next_id
