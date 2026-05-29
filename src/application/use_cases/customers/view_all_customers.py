"""Use case for listing customers."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.pagination import (
    PageQuery,
    PageResult,
    validate_page,
    validate_unpaginated_offset,
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
        if query.limit is None:
            validate_unpaginated_offset(query.offset)
            return PageResult(
                items=tuple(self._customers.list_all()),
                total=None,
                limit=None,
                offset=query.offset,
            )

        validate_page(query.limit, query.offset)
        if query.include_total:
            customers, total = self._customers.list_page_with_total(limit=query.limit, offset=query.offset)
        else:
            customers = self._customers.list_page(limit=query.limit, offset=query.offset)
            total = None

        return PageResult(
            items=tuple(customers),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
