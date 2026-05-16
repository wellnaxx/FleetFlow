"""Use case for listing customers."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.customer import Customer
from src.domain.enums.auth import Permission
from src.ports.output.customer_repository import CustomerRepositoryPort


class ViewAllCustomersUseCase(AuthorizedUseCase[list[Customer]]):
    """List all customers from the repository."""

    def __init__(self, customers: CustomerRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            customers: Repository used to list customers.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._customers = customers

    @requires(Permission.CUSTOMER_VIEW)
    def execute(self) -> list[Customer]:
        """Return all persisted customers.

        Returns:
            Customer entities currently stored in the repository.
        """
        return self._customers.list_all()
