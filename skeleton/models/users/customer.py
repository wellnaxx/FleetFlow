from models.users.user import User
from models.delivery_package import DeliveryPackage

class Customer(User):
    def __init__(self, name, phone_number, email):
        super().__init__(name, phone_number, email)
        self._delivery_packages: list[DeliveryPackage] = []

    @property
    def delivery_packages(self):
        return tuple(self._delivery_packages)
    
    def _existing_package(self, package: DeliveryPackage) -> bool:
        return any(p.package_id == package.package_id for p in self._delivery_packages)


    def add_package(self, package: DeliveryPackage):
        if self._existing_package(package):
            raise ValueError(f"Package with id {package.package_id} is already assigned to this customer.")
        self._delivery_packages.append(package)

    def remove_package(self, package: DeliveryPackage):
        if not self._existing_package(package):
            raise ValueError(f"Package with id {package.package_id} does not exist.")
        self._delivery_packages.remove(package)
    


    