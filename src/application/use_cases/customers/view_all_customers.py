from src.domain.entities.customer import Customer
from src.ports.output.customer_repository import CustomerRepositoryPort


class ViewAllCustomersUseCase:
    """List all customers from the repository."""

    def __init__(self, customers: CustomerRepositoryPort) -> None:
        self._customers = customers

    def execute(self) -> list[Customer]:
        """Return all persisted customers."""
        return self._customers.list_all()
