"""Query handler for paginated customer browsing."""

from src.application.queries.customers.view_all_customers import ViewAllCustomersQuery
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.application.use_cases.pagination import PageResult
from src.domain.entities.customer import Customer


class ViewAllCustomersQueryHandler:
    """Adapt a customer listing query to the existing workflow."""

    def __init__(self, use_case: ViewAllCustomersUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized customer-listing workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: ViewAllCustomersQuery) -> PageResult[Customer]:
        """Return customers selected by the pagination request.

        Args:
            query: Customer pagination request.

        Returns:
            Page of customers produced by the use case.

        Raises:
            Exception: Propagates authorization, validation, persistence, and
                other failures raised by the use case.
        """
        return self._use_case.execute(query.page)
