from src.domain.entities.delivery_package import DeliveryPackage


class InMemoryPackageRepository:
    def __init__(self) -> None:
        self._packages: dict[int, DeliveryPackage] = {}
        self._next_id: int = 1

    def peek_next_id(self) -> int:
        return self._next_id

    def add(self, package: DeliveryPackage) -> None:
        if package.package_id in self._packages:
            raise ValueError(f"Package with id {package.package_id} already exists.")
        self._packages[package.package_id] = package

        self._next_id = max(self._next_id, package.package_id + 1)

    def remove(self, package_id: int) -> None:
        if package_id in self._packages:
            del self._packages[package_id]

    def get_by_id(self, package_id: int) -> DeliveryPackage | None:
        return self._packages.get(package_id)

    def list_all(self) -> list[DeliveryPackage]:
        return [self._packages[package_id] for package_id in sorted(self._packages)]

    def list_unassigned(self) -> list[DeliveryPackage]:
        return [package for package in self.list_all() if package.route is None]

    def replace_packages(self, packages_by_id: dict[int, DeliveryPackage], next_id: int) -> None:
        self._packages = dict(packages_by_id)
        self._next_id = next_id
