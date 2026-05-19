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
    def execute(self, limit: int | None = None, offset: int = 0) -> list[Customer]:
        """Return all persisted customers.

        Args:
            limit: Optional maximum number of customers to return.
            offset: Number of customers to skip when `limit` is provided.

        Returns:
            Customer entities currently stored in the repository.

        Raises:
            ValueError: If pagination arguments are invalid.
        """
        if limit is None:
            return self._customers.list_all()

        if limit < 1:
            raise ValueError("Limit must be greater than zero.")
        if offset < 0:
            raise ValueError("Offset must be greater than or equal to zero.")

        return self._customers.list_page(limit=limit, offset=offset)

    @requires(Permission.CUSTOMER_VIEW)
    def count(self) -> int:
        """Return the total number of persisted customers."""
        return self._customers.count_all()
