"""Use case for viewing one package."""

from src.domain.entities.delivery_package import DeliveryPackage
from src.ports.output.package_repository import PackageRepositoryPort


class ViewPackageUseCase:
    """Fetch one package by id."""

    def __init__(self, packages: PackageRepositoryPort) -> None:
        """Initialize the use case.

        Args:
            packages: Repository used to fetch packages.
        """
        self._packages = packages

    def execute(self, package_id: int) -> DeliveryPackage:
        """Return one package by id.

        Args:
            package_id: Identifier of the package to fetch.

        Returns:
            The matching package entity.

        Raises:
            ValueError: If the package does not exist.
        """
        package = self._packages.get_by_id(package_id)
        if not package:
            raise ValueError(f"Package with ID {package_id} not found")
        return package
