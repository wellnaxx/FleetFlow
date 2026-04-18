from src.domain.entities.delivery_package import DeliveryPackage
from src.ports.output.package_repository import PackageRepositoryPort


class ViewPackageUseCase:
    def __init__(self, packages: PackageRepositoryPort) -> None:
        self._packages = packages

    def execute(self, package_id: int) -> DeliveryPackage:
        package = self._packages.get_by_id(package_id)
        if not package:
            raise ValueError(f"Package with ID {package_id} not found")
        return package