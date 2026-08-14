"""Query handler for paginated route browsing."""

from src.application.queries.routes.view_all_routes import ViewAllRoutesQuery
from src.application.use_cases.pagination import PageResult
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.domain.entities.delivery_route import DeliveryRoute


class ViewAllRoutesQueryHandler:
    """Adapt a route listing query to the existing workflow."""

    def __init__(self, use_case: ViewAllRoutesUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized route-listing workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: ViewAllRoutesQuery) -> PageResult[DeliveryRoute]:
        """Return routes selected by the pagination request.

        Args:
            query: Route pagination request.

        Returns:
            Page of routes produced by the use case.

        Raises:
            Exception: Propagates authorization, validation, persistence, and
                other failures raised by the use case.
        """
        return self._use_case.execute(query.page)
