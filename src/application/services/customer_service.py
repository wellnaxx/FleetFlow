from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo
from src.ports.output.customer_repository import CustomerRepositoryPort


class CustomerService:
    def __init__(self, customers: CustomerRepositoryPort) -> None:
        self._customers = customers

    def find_existing_customer(self, name: str, email: str = "", phone: str = "") -> Customer | None:
        name = (name or "").strip()
        email = (email or "").strip().lower()
        phone = "".join(ch for ch in (phone or "") if ch.isdigit())

        by_email = self._customers.get_by_email(email) if email else None
        by_phone = self._customers.get_by_phone(phone) if phone else None

        if email and phone:
            return self._resolve_email_and_phone(name, by_email, by_phone)

        if email and by_email:
            self._ensure_name_matches(name, by_email)
            return by_email

        if phone and by_phone:
            self._ensure_name_matches(name, by_phone)
            return by_phone

        return self._resolve_name_only(name, email, phone)

    def create(self, name: str, email: str = "", phone: str = "") -> Customer:
        contact_info = ContactInfo(name=name, email=email, phone_number=phone)
        customer = Customer(customer_id=self._customers.next_id(), contact=contact_info)
        self._customers.add(customer)
        return customer

    def _resolve_email_and_phone(
        self, name: str, by_email: Customer | None, by_phone: Customer | None
    ) -> Customer | None:
        if by_email and by_phone:
            if by_email.customer_id != by_phone.customer_id:
                raise ValueError(
                    f"Email belongs to customer ID: {by_email.customer_id}, "
                    f"and phone belongs to customer ID: {by_phone.customer_id}."
                )
            if name and not self._same_name(name, by_email.name):
                raise ValueError(
                    f"Provided name '{name}' does not match existing customer "
                    f"ID {by_email.customer_id} ('{by_email.name}')."
                )
            return by_email

        if by_email and not by_phone:
            if name and not self._same_name(name, by_email.name):
                raise ValueError(
                    f"Email already in use by customer ID {by_email.customer_id} ('{by_email.name}')."
                )
            return by_email

        if by_phone and not by_email:
            if name and not self._same_name(name, by_phone.name):
                raise ValueError(
                    f"Phone already in use by customer ID {by_phone.customer_id} ('{by_phone.name}')."
                )
            return by_phone
        return None

    def _resolve_name_only(self, name: str, email: str, phone: str) -> Customer | None:
        if email or phone or not name:
            return None

        candidates = self._customers.list_by_name(name)
        name_only = [
            customer for customer in candidates if customer.email == "" and customer.phone_number == ""
        ]

        if len(candidates) == 1 and len(name_only) == 1:
            return name_only[0]

        return None

    def _ensure_name_matches(self, name: str, customer: Customer) -> None:
        if name and not self._same_name(name, customer.name):
            raise ValueError(
                f"Provided name {name} does not match existing customer ID {customer.customer_id} ('{customer.name}')."  # noqa: E501
            )

    def _same_name(self, input_name: str, customer_name: str) -> bool:
        return (input_name or "").strip().casefold() == (customer_name or "").strip().casefold()
 