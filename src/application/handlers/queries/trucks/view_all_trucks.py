"""Query handler for listing all trucks."""

from src.application.queries.trucks.view_all_trucks import ViewAllTrucksQuery
from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase
from src.domain.entities.truck import Truck


class ViewAllTrucksQueryHandler:
    """Delegate a fieldless truck query to the listing workflow."""

    def __init__(self, use_case: ViewAllTrucksUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized truck-listing workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: ViewAllTrucksQuery) -> list[Truck]:
        """Return all visible trucks.

        Args:
            query: Fieldless message selecting the truck-listing workflow.

        Returns:
            Trucks produced by the use case.

        Raises:
            Exception: Propagates authorization, persistence, and other
                failures raised by the use case.
        """
        del query
        return self._use_case.execute()
