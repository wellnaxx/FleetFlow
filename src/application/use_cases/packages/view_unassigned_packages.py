"""Use case for listing unassigned packages."""

from src.domain.entities.delivery_package import DeliveryPackage
from src.ports.output.package_repository import PackageRepositoryPort


class ViewUnassignedPackagesUseCase:
    """List packages that are not assigned to any route."""

    def __init__(self, packages: PackageRepositoryPort) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to query unassigned packages.
        """
        self._packages = packages

    def execute(self) -> list[DeliveryPackage]:
        """Return all packages that are currently unassigned.

        Returns:
            Packages without a route assignment.
        """
        return self._packages.list_unassigned()
