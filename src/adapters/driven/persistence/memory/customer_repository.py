from src.domain.entities.customer import Customer


class InMemoryCustomerRepository:
    """Store customers in process memory for runtime use."""

    def __init__(self) -> None:
        self._customers_by_id: dict[int, Customer] = {}
        self._id_by_email: dict[str, int] = {}
        self._id_by_phone: dict[str, int] = {}
        self._next_id: int = 1

    def peek_next_id(self) -> int:
        """Return the next customer id without incrementing the counter."""
        return self._next_id

    def add(self, customer: Customer) -> None:
        """Add a customer and update uniqueness indexes.

        Args:
            customer: Customer entity to store.

        Raises:
            ValueError: If the id already exists or the email/phone is already
                used by another customer.
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

    def remove(self, customer_id: int) -> None:
        """Remove a customer and any email/phone indexes for that record."""
        customer = self._customers_by_id.get(customer_id)
        if customer is None:
            return

        if customer.email:
            self._id_by_email.pop(customer.email, None)

        if customer.phone_number:
            self._id_by_phone.pop(customer.phone_number, None)

        self._customers_by_id.pop(customer_id, None)

    def get_by_id(self, customer_id: int) -> Customer | None:
        """Return a customer by id, if present."""
        return self._customers_by_id.get(customer_id, None)

    def get_by_email(self, email: str) -> Customer | None:
        """Return a customer by email, if present."""
        customer_id = self._id_by_email.get(email, None)
        if customer_id is None:
            return None
        return self._customers_by_id[customer_id]

    def get_by_phone(self, phone: str) -> Customer | None:
        """Return a customer by phone number, if present."""
        customer_id = self._id_by_phone.get(phone, None)
        if customer_id is None:
            return None
        return self._customers_by_id[customer_id]

    def list_by_name(self, name: str) -> list[Customer]:
        """Return customers whose normalized names match the input."""
        return [
            customer
            for customer in self.list_all()
            if (customer.name or "").strip().casefold() == (name or "").strip().casefold()
        ]

    def list_all(self) -> list[Customer]:
        """Return all customers ordered by id."""
        return [self._customers_by_id[customer_id] for customer_id in sorted(self._customers_by_id)]

    def replace_customers(self, customers_by_id: dict[int, Customer], next_id: int) -> None:
        """Replace the full customer state from a snapshot load."""
        self._customers_by_id = dict(customers_by_id)
        self._id_by_email = {
            customer.email: customer.customer_id
            for customer in customers_by_id.values()
            if customer.email
        }
        self._id_by_phone = {
            customer.phone_number: customer.customer_id
            for customer in customers_by_id.values()
            if customer.phone_number
        }
        self._next_id = next_id
