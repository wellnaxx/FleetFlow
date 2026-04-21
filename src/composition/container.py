from src.adapters.driven.persistence.application_data.customer_repository import (
    ApplicationDataCustomerRepository,
)
from src.adapters.driven.persistence.application_data.package_repository import ApplicationDataPackageRepository
from src.adapters.driven.persistence.application_data.route_repository import ApplicationDataRouteRepository
from src.application.services.customer_service import CustomerService
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.application.use_cases.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteUseCase
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from src.core.application_data import ApplicationData


class Container:
    def __init__(self, app_data: ApplicationData) -> None:
        self.package_repo = ApplicationDataPackageRepository(app_data)
        self.customer_repo = ApplicationDataCustomerRepository(app_data)
        self.route_repo = ApplicationDataRouteRepository(app_data)

        self.customer_service = CustomerService(self.customer_repo)

        self.vehicle_manager = app_data.vehicle_manager

        self.create_package_use_case = CreatePackageUseCase(
            self.customer_service,
            self.package_repo,
        )
        self.view_package_use_case = ViewPackageUseCase(self.package_repo)
        self.view_all_packages_use_case = ViewAllPackagesUseCase(self.package_repo)
        self.remove_package_use_case = RemovePackageUseCase(self.package_repo)
        self.view_unassigned_packages_use_case = ViewUnassignedPackagesUseCase(self.package_repo)
        self.view_all_customers_use_case = ViewAllCustomersUseCase(self.customer_repo)
        self.view_route_use_case = ViewRouteUseCase(self.route_repo)
        self.view_all_routes_use_case = ViewAllRoutesUseCase(self.route_repo)
        self.view_routes_in_progress_use_case = ViewRoutesInProgressUseCase(self.route_repo)
        self.create_route_use_case = CreateRouteUseCase(self.route_repo)
        self.remove_route_use_case = RemoveRouteUseCase(self.route_repo)
        self.assign_truck_to_route_use_case = AssignTruckToRouteUseCase(self.route_repo, self.vehicle_manager)
        self.find_suitable_trucks_for_route_use_case = FindSuitableTrucksForRouteUseCase(
            self.route_repo, self.vehicle_manager
        )
