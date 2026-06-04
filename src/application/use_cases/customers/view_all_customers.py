"""Use case for listing customers."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.pagination import (
    PageQuery,
    PageResult,
    execute_page_query,
)
from src.domain.entities.customer import Customer
from src.domain.enums.auth import Permission
from src.ports.output.customer_repository import CustomerRepositoryPort


class ViewAllCustomersUseCase(AuthorizedUseCase[PageResult[Customer]]):
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
    def execute(self, query: PageQuery = PageQuery()) -> PageResult[Customer]:
        """Return all persisted customers.

        Args:
            query: Pagination request. Defaults to a full uncounted list.

        Returns:
            Customer page result.

        Raises:
            ValidationError: If pagination arguments are invalid.
        """
        return execute_page_query(
            query=query,
            list_all=self._customers.list_all,
            list_page=lambda limit, offset: self._customers.list_page(limit=limit, offset=offset),
            list_page_with_total=lambda limit, offset: self._customers.list_page_with_total(
                limit=limit, offset=offset
            ),
        )
