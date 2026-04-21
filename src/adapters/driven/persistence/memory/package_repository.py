from src.domain.entities.delivery_package import DeliveryPackage


class InMemoryPackageRepository:
    def __init__(self) -> None:
        self._packages: dict[int, DeliveryPackage] = {}

    def next_id(self) -> int:
        if not self._packages:
            return 1
        return max(self._packages.keys()) + 1

    def add(self, package: DeliveryPackage) -> None:
        if package.package_id in self._packages:
            raise ValueError(f"Package with id {package.package_id} already exists.")
        self._packages[package.package_id] = package

    def remove(self, package_id: int) -> None:
        if package_id in self._packages:
            del self._packages[package_id]

    def get_by_id(self, package_id: int) -> DeliveryPackage | None:
        return self._packages.get(package_id)
    
    def list_all(self) -> list[DeliveryPackage]:
        return list(self._packages.values())
    
    def list_unassigned(self) -> list[DeliveryPackage]:
        return [package for package in self._packages.values() if package.route is None]
