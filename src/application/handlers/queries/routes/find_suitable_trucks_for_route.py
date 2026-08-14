"""Query handler for route-to-truck suitability searches."""

from src.application.queries.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteQuery
from src.application.use_cases.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteUseCase
from src.domain.entities.truck import Truck


class FindSuitableTrucksForRouteQueryHandler:
    """Adapt a route identifier to the truck-suitability workflow."""

    def __init__(self, use_case: FindSuitableTrucksForRouteUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized truck-suitability workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: FindSuitableTrucksForRouteQuery) -> list[Truck]:
        """Return trucks suitable for the identified route.

        Args:
            query: Identifier of the route to evaluate.

        Returns:
            Suitable trucks produced by the use case.

        Raises:
            Exception: Propagates authorization, lookup, domain, persistence,
                and other failures raised by the use case.
        """
        return self._use_case.execute(query.route_id)
