"""Query handler for paginated package browsing."""

from src.application.queries.packages.view_all_packages import ViewAllPackagesQuery
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.pagination import PageResult
from src.domain.entities.delivery_package import DeliveryPackage


class ViewAllPackagesQueryHandler:
    """Adapt a package listing query to the existing workflow."""

    def __init__(self, use_case: ViewAllPackagesUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized package-listing workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: ViewAllPackagesQuery) -> PageResult[DeliveryPackage]:
        """Return packages selected by the pagination request.

        Args:
            query: Package pagination request.

        Returns:
            Page of packages produced by the use case.

        Raises:
            Exception: Propagates authorization, validation, persistence, and
                other failures raised by the use case.
        """
        return self._use_case.execute(query.page)
