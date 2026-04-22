from src.domain.entities.delivery_package import DeliveryPackage
from src.ports.output.package_repository import PackageRepositoryPort


class ViewUnassignedPackagesUseCase:
    """List packages that are not assigned to any route."""

    def __init__(self, packages: PackageRepositoryPort) -> None:
        self._packages = packages

    def execute(self) -> list[DeliveryPackage]:
        """Return all packages that are currently unassigned."""
        return self._packages.list_unassigned()
