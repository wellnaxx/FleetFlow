from src.domain.entities.delivery_package import DeliveryPackage
from src.ports.output.package_repository import PackageRepositoryPort


class ViewUnassignedPackagesUseCase:
    def __init__(self, packages: PackageRepositoryPort) -> None:
        self._packages = packages

    def execute(self) -> list[DeliveryPackage]:
        return self._packages.list_unassigned()