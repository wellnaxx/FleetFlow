from src.domain.entities.delivery_package import DeliveryPackage
from src.ports.output.package_repository import PackageRepositoryPort


class ViewAllPackagesUseCase:
    """List all packages from the repository."""

    def __init__(self, packages: PackageRepositoryPort) -> None:
        self._packages = packages

    def execute(self) -> list[DeliveryPackage]:
        """Return all persisted packages."""
        return self._packages.list_all()
