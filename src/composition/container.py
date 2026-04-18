from src.adapters.driven.persistence.application_data.customer_repository import (
    ApplicationDataCustomerRepository,
)
from src.adapters.driven.persistence.application_data.package_repository import ApplicationDataPackageRepository
from src.application.services.customer_service import CustomerService
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.core.application_data import ApplicationData


class Container:
    def __init__(self, app_data: ApplicationData) -> None:
        self.package_repo = ApplicationDataPackageRepository(app_data)
        self.customer_repo = ApplicationDataCustomerRepository(app_data)

        self.customer_service = CustomerService(self.customer_repo)

        self.create_package_use_case = CreatePackageUseCase(
            self.customer_service,
            self.package_repo,
        )
        self.view_package_use_case = ViewPackageUseCase(self.package_repo)
        self.view_all_packages_use_case = ViewAllPackagesUseCase(self.package_repo)
        self.remove_package_use_case = RemovePackageUseCase(self.package_repo)
        self.view_unassigned_packages_use_case = ViewUnassignedPackagesUseCase(self.package_repo)
        self.view_all_customers_use_case = ViewAllCustomersUseCase(self.customer_repo)
