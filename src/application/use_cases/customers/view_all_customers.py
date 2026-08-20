"""Use case for listing customers."""

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.queries.customers.view_all_customers import ViewAllCustomersQuery
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.pagination import (
    PageResult,
    execute_page_query,
)
from src.domain.entities.customer import Customer
from src.domain.enums.auth import Permission
from src.ports.output.customer_repository import CustomerRepositoryPort


class ViewAllCustomersUseCase(AuthorizedUseCase[PageResult[Customer]]):
    """Browse customers under customer-view authorization.

    The workflow accepts the published customer query directly so command-line
    and HTTP adapters share one typed application boundary. Authorization
    denials are recorded by the inherited event-aware authorization behavior.
    """

    def __init__(self, customers: CustomerRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            customers: Repository used to list customers.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._customers = customers

    @requires(
        Permission.CUSTOMER_VIEW,
        operation=AuthorizationOperation.CUSTOMER_LIST,
        target_resource_type=AuditResourceType.CUSTOMER,
        target_resource_id_resolver=None,
    )
    def execute(self, query: ViewAllCustomersQuery) -> PageResult[Customer]:
        """Return all persisted customers.

        Args:
            query: Customer query containing pagination and total-count
                selection.

        Returns:
            Customer page result.

        Raises:
            PermissionError: If no principal is authenticated or the current
                principal lacks customer-view permission.
            ValidationError: If pagination arguments are invalid.
            DatabaseError: If customer retrieval fails.
        """
        return execute_page_query(
            query=query.page,
            list_all=self._customers.list_all,
            list_page=lambda limit, offset: self._customers.list_page(limit=limit, offset=offset),
            list_page_with_total=lambda limit, offset: self._customers.list_page_with_total(
                limit=limit, offset=offset
            ),
        )
