from src.core.application_data import ApplicationData
from src.domain.entities.customer import Customer


class ApplicationDataCustomerRepository:
    def __init__(self, app_data: ApplicationData) -> None:
        self._app_data = app_data

    def next_id(self) -> int:
        return self._app_data.allocate_customer_id()
    
    def add(self, customer: Customer) -> None:
        customers = self._app_data.customer_store
        if any(existing.customer_id == customer.customer_id for existing in customers):
            raise ValueError(f"Customer with id {customer.customer_id} already exists.")
        customers.append(customer)

        if customer.email:
            self._app_data.customer_email_store[customer.email] = customer
        
        if customer.phone_number:
            self._app_data.customer_phone_store[customer.phone_number] = customer

    def remove(self, customer_id: int) -> None:
        customers = self._app_data.customer_store
        for idx, customer in enumerate(customers):
            if customer.customer_id == customer_id:
                customers.pop(idx)
                
                if customer.email:
                    self._app_data.customer_email_store.pop(customer.email, None)
                
                if customer.phone_number:
                    self._app_data.customer_phone_store.pop(customer.phone_number, None)
                return

    def get_by_id(self, customer_id: int) -> Customer | None:
        for customer in self._app_data.customer_store:
            if customer.customer_id == customer_id:
                return customer
        return None

    def get_by_email(self, email: str) -> Customer | None:
        if not email:
            return None
        return self._app_data.customer_email_store.get(email)

    def get_by_phone(self, phone: str) -> Customer | None:
        if not phone:
            return None
        return self._app_data.customer_phone_store.get(phone)

    def list_by_name(self, name: str) -> list[Customer]:
        normalized = (name or "").strip().casefold()
        return [
            customer
            for customer in self._app_data.customer_store
            if customer.name.strip().casefold() == normalized
        ]

    def list_all(self) -> list[Customer]:
        return list(self._app_data.customer_store)