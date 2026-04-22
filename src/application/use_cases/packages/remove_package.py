from src.domain.entities.delivery_package import DeliveryPackage
from src.ports.output.package_repository import PackageRepositoryPort


class RemovePackageUseCase:
    """Remove a package from the repository and any assigned route."""

    def __init__(self, packages: PackageRepositoryPort) -> None:
        self._packages = packages

    def execute(self, package_id: int) -> DeliveryPackage:
        """Remove a package by id.

        Args:
            package_id: Identifier of the package to remove.

        Returns:
            The removed package entity.

        Raises:
            ValueError: If the package does not exist.
        """
        package = self._packages.get_by_id(package_id)
        if package is None:
            raise ValueError(f"Package with ID {package_id} not found")

        if package.route is not None:
            package.route.detach_package(package)

        self._packages.remove(package_id)
        return package
