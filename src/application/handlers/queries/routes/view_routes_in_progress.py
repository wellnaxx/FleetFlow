"""Query handler for routes active at a business timestamp."""

from src.application.queries.routes.view_routes_in_progress import ViewRoutesInProgressQuery
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.route_schedule import RoutePosition


class ViewRoutesInProgressQueryHandler:
    """Adapt a timed route query to the in-progress workflow."""

    def __init__(self, use_case: ViewRoutesInProgressUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized active-route workflow to invoke.
        """
        self._use_case = use_case

    def execute(
        self,
        query: ViewRoutesInProgressQuery,
    ) -> list[tuple[DeliveryRoute, RoutePosition]]:
        """Return routes active at the query's business timestamp.

        Args:
            query: App-local time used to calculate route positions.

        Returns:
            Active routes paired with their calculated positions.

        Raises:
            Exception: Propagates authorization, domain, persistence, and other
                failures raised by the use case.
        """
        return self._use_case.execute(query.now)
