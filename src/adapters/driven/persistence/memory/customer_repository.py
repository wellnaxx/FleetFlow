from src.domain.entities.customer import Customer


class InMemoryCustomerRepository:
    def __init__(self) -> None:
        self._customers_by_id: dict[int, Customer] = {}
        self._id_by_email: dict[str, int] = {}
        self._id_by_phone: dict[str, int] = {}

    def next_id(self) -> int:
        if not self._customers_by_id:
            return 1
        return max(self._customers_by_id.keys()) + 1

    def add(self, customer: Customer) -> None:
        self._customers_by_id[customer.customer_id] = customer
        if customer.email:
            self._id_by_email[customer.email] = customer.customer_id
        if customer.phone_number:
            self._id_by_phone[customer.phone_number] = customer.customer_id

    def remove(self, customer_id: int) -> None:
        customer = self._customers_by_id.get(customer_id)
        if customer is None:
            return

        if customer.email:
            self._id_by_email.pop(customer.email, None)

        if customer.phone_number:
            self._id_by_phone.pop(customer.phone_number, None)

        self._customers_by_id.pop(customer_id, None)

    def get_by_id(self, customer_id: int) -> Customer | None:
        return self._customers_by_id.get(customer_id, None)

    def get_by_email(self, email: str) -> Customer | None:
        customer_id = self._id_by_email.get(email, None)
        if customer_id is None:
            return None
        return self._customers_by_id[customer_id]

    def get_by_phone(self, phone: str) -> Customer | None:
        customer_id = self._id_by_phone.get(phone, None)
        if customer_id is None:
            return None
        return self._customers_by_id[customer_id]

    def list_by_name(self, name: str) -> list[Customer]:
        return [
            customer
            for customer in self._customers_by_id.values()
            if (customer.name or "").strip().casefold() == (name or "").strip().casefold()
        ]

    def list_all(self) -> list[Customer]:
        return list(self._customers_by_id.values())
