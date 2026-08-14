"""Query handler for retrieving one package."""

from src.application.queries.packages.view_package import ViewPackageQuery
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.domain.entities.delivery_package import DeliveryPackage


class ViewPackageQueryHandler:
    """Adapt an identifier query to the package lookup workflow."""

    def __init__(self, use_case: ViewPackageUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized package-lookup workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: ViewPackageQuery) -> DeliveryPackage:
        """Return the identified package.

        Args:
            query: Identifier of the package to retrieve.

        Returns:
            Package returned by the use case.

        Raises:
            Exception: Propagates authorization, lookup, persistence, and other
                failures raised by the use case.
        """
        return self._use_case.execute(query.package_id)
