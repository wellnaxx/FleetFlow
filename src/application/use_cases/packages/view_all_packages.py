"""Use case for listing all packages."""

from src.domain.entities.delivery_package import DeliveryPackage
from src.ports.output.package_repository import PackageRepositoryPort


class ViewAllPackagesUseCase:
    """List all packages from the repository."""

    def __init__(self, packages: PackageRepositoryPort) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to list packages.
        """
        self._packages = packages

    def execute(self) -> list[DeliveryPackage]:
        """Return all persisted packages.

        Returns:
            Package entities currently stored in the repository.
        """
        return self._packages.list_all()
