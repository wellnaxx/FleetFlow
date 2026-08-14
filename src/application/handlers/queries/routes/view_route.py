"""Query handler for retrieving one delivery route."""

from src.application.queries.routes.view_route import ViewRouteQuery
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.domain.entities.delivery_route import DeliveryRoute


class ViewRouteQueryHandler:
    """Adapt an identifier query to the route lookup workflow."""

    def __init__(self, use_case: ViewRouteUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized route-lookup workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: ViewRouteQuery) -> DeliveryRoute:
        """Return the identified route.

        Args:
            query: Identifier of the route to retrieve.

        Returns:
            Route returned by the use case.

        Raises:
            Exception: Propagates authorization, lookup, persistence, and other
                failures raised by the use case.
        """
        return self._use_case.execute(query.route_id)
