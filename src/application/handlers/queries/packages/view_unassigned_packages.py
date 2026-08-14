"""Query handler for paginated unassigned-package browsing."""

from src.application.queries.packages.view_unassigned_packages import ViewUnassignedPackagesQuery
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.application.use_cases.pagination import PageResult
from src.domain.entities.delivery_package import DeliveryPackage


class ViewUnassignedPackagesQueryHandler:
    """Adapt an unassigned-package query to the existing workflow."""

    def __init__(self, use_case: ViewUnassignedPackagesUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized unassigned-package workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: ViewUnassignedPackagesQuery) -> PageResult[DeliveryPackage]:
        """Return unassigned packages selected by pagination.

        Args:
            query: Unassigned-package pagination request.

        Returns:
            Page of unassigned packages produced by the use case.

        Raises:
            Exception: Propagates authorization, validation, persistence, and
                other failures raised by the use case.
        """
        return self._use_case.execute(query.page)
