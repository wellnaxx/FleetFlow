from datetime import datetime

from src.adapters.driven.persistence.json.world_state_persistence import JsonWorldStatePersistence
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.world_state_gateway import (
    InMemoryWorldStateGateway,
    InMemoryWorldStateRuntime,
)
from src.application.config.state_persistence import DEFAULT_WORLD_STATE_PATH
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
from src.application.services.customer_service import CustomerService
from src.application.services.heartbeat_service import HeartbeatService
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_service import WorldStateSnapshotService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.application.use_cases.auth.who_am_i import WhoAmIUseCase
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.application.use_cases.routes.assign_packages_to_route import AssignPackagesToRouteUseCase
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.application.use_cases.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageUseCase,
)
from src.application.use_cases.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteUseCase
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from src.application.use_cases.state.advance_world_state import AdvanceWorldStateUseCase
from src.application.use_cases.state.load_world import LoadWorldStateUseCase
from src.application.use_cases.state.save_world import SaveWorldStateUseCase
from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase
from src.domain.services.vehicle_manager import VehicleManager


class Container:
    """Wire repositories, services, and use cases for the CLI application."""

    def __init__(self, auth: AuthService) -> None:
        """Construct the application dependency graph.

        Args:
            auth: Shared authentication service used by auth-related use cases
                and authorization checks.
        """
        self.package_repo = InMemoryPackageRepository()
        self.customer_repo = InMemoryCustomerRepository()
        self.route_repo = InMemoryRouteRepository()

        self.customer_service = CustomerService(self.customer_repo)

        self.vehicle_manager = VehicleManager()
        self.auth = auth
        self.authz = AuthorizationService(auth.current_user)

        self.reconciler = WorldStateReconciliationService()

        self.heartbeat_service = HeartbeatService(self.route_repo, self.reconciler)
        self.advance_world_state_use_case = AdvanceWorldStateUseCase(self.heartbeat_service)

        self.world_state_runtime = InMemoryWorldStateRuntime(
            customer_repo=self.customer_repo,
            package_repo=self.package_repo,
            route_repo=self.route_repo,
            vehicle_manager=self.vehicle_manager,
        )
        self.world_state_snapshot_service = WorldStateSnapshotService(
            customer_repo=self.customer_repo,
            package_repo=self.package_repo,
            route_repo=self.route_repo,
            vehicle_manager=self.vehicle_manager,
            runtime_state=self.world_state_runtime,
            reconciler=self.reconciler,
        )
        self.world_state_gateway = InMemoryWorldStateGateway(
            snapshot_service=self.world_state_snapshot_service,
        )
        self.world_state_persistence = JsonWorldStatePersistence()
        self.save_world_state_use_case = SaveWorldStateUseCase(
            self.world_state_gateway,
            self.world_state_persistence,
        )
        self.load_world_state_use_case = LoadWorldStateUseCase(
            self.world_state_gateway,
            self.world_state_persistence,
        )
        self.default_world_state_path = DEFAULT_WORLD_STATE_PATH

        self.login_use_case = LoginUseCase(self.auth)
        self.logout_use_case = LogoutUseCase(self.auth)
        self.who_am_i_use_case = WhoAmIUseCase(self.auth)
        self.register_user_use_case = RegisterUserUseCase(self.auth)
        self.change_password_use_case = ChangePasswordUseCase(self.auth)

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
        self.assign_packages_to_route_use_case = AssignPackagesToRouteUseCase(
            self.route_repo,
            self.package_repo,
            clock=datetime.now,
        )
        self.find_suitable_routes_for_package_use_case = FindSuitableRoutesForPackageUseCase(
            self.route_repo,
            self.package_repo,
            clock=datetime.now,
        )
        self.view_all_trucks_use_case = ViewAllTrucksUseCase(self.vehicle_manager)
