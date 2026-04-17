from src.core.application_data import ApplicationData
from src.domain.entities.delivery_package import DeliveryPackage


class ApplicationDataPackageRepository:
    def __init__(self, app_data: ApplicationData) -> None:
        self._app_data = app_data

    def next_id(self) -> int:
       return self._app_data.allocate_package_id()

    def add(self, package: DeliveryPackage) -> None:
        packages = self._app_data.package_store
        if any(existing.package_id == package.package_id for existing in packages):
            raise ValueError(f"Package with id {package.package_id} already exists.")
        packages.append(package)

    def remove(self, package_id: int) -> None:
        packages = self._app_data.package_store
        for i, package in enumerate(packages):
            if package.package_id == package_id:
                packages.pop(i)
                return

    def get_by_id(self, package_id: int) -> DeliveryPackage | None:
        for package in self._app_data.package_store:
            if package.package_id == package_id:
                return package
        return None

    def list_all(self) -> list[DeliveryPackage]:
        return list(self._app_data.package_store)

    def list_unassigned(self) -> list[DeliveryPackage]:
        return [package for package in self._app_data.package_store if package.route is None]
