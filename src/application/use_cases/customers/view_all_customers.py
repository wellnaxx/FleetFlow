from src.domain.entities.customer import Customer
from src.ports.output.customer_repository import CustomerRepositoryPort


class ViewAllCustomersUseCase:
    def __init__(self, customers: CustomerRepositoryPort) -> None:
        self._customers = customers

    def execute(self) -> list[Customer]:
        return self._customers.list_all()