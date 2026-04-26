"""Use case for listing customers."""

from src.domain.entities.customer import Customer
from src.ports.output.customer_repository import CustomerRepositoryPort


class ViewAllCustomersUseCase:
    """List all customers from the repository."""

    def __init__(self, customers: CustomerRepositoryPort) -> None:
        """Initialize the use case.

        Args:
            customers: Repository used to list customers.
        """
        self._customers = customers

    def execute(self) -> list[Customer]:
        """Return all persisted customers.

        Returns:
            Customer entities currently stored in the repository.
        """
        return self._customers.list_all()
