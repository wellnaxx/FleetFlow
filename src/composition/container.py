"""Application composition root for CLI runtime dependencies."""

from datetime import datetime

from src.adapters.driven.persistence.database.repositories.customer_repository import PostgresCustomerRepository
from src.adapters.driven.persistence.database.repositories.package_repository import PostgresPackageRepository
from src.adapters.driven.persistence.database.repositories.route_repository import PostgresRouteRepository
from src.adapters.driven.persistence.database.repositories.truck_repository import PostgresTruckRepository
from src.adapters.driven.persistence.database.unit_of_work import PostgresUnitOfWork
from src.adapters.driven.persistence.json.config import get_json_config
from src.adapters.driven.persistence.json.world_state_persistence import JsonWorldStatePersistence
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.truck_repository import InMemoryTruckRepository
from src.adapters.driven.persistence.memory.unit_of_work import InMemoryUnitOfWork
from src.adapters.driven.persistence.memory.world_state_gateway import (
    InMemoryWorldStateGateway,
    InMemoryWorldStateRuntime,
)
from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot
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
from src.composition.config import AppConfig, PersistenceBackend, get_app_config
from src.composition.seed_fleet import seed_fleet_if_empty
from src.domain.services.vehicle_manager import VehicleManager


class UnsupportedWorldStateGateway:
    """World-state gateway placeholder for backends without JSON import/export."""

    def __init__(self, message: str) -> None:
        """Initialize the unsupported gateway.

        Args:
            message: Error message raised when snapshot operations are called.
        """
        self._message = message

    def build_snapshot(self) -> WorldStateSnapshot:
        """Raise because this backend cannot export world-state snapshots yet.

        Raises:
            NotImplementedError: Always raised.
        """
        raise NotImplementedError(self._message)

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        """Raise because this backend cannot import world-state snapshots yet.

        Args:
            snapshot: Snapshot that cannot currently be applied.

        Raises:
            NotImplementedError: Always raised.
        """
        raise NotImplementedError(self._message)


class Container:
    """Wire repositories, services, and use cases for the CLI application."""

    def __init__(self, auth: AuthService, config: AppConfig | None = None) -> None:
        """Construct the application dependency graph.

        Args:
            auth: Shared authentication service used by auth-related use cases
                and authorization checks.
            config: Application configuration. When omitted, it is loaded from
                the environment.
        """
        config = config or get_app_config()

        if config.persistence_backend is PersistenceBackend.MEMORY:
            self._wire_memory()
            self.autosave_enabled = True
        elif config.persistence_backend is PersistenceBackend.POSTGRES:
            self._wire_postgres()
            self.autosave_enabled = False
        else:
            raise ValueError(f"Unsupported persistence backend: {config.persistence_backend!r}")

        seed_fleet_if_empty(self.truck_repo)
        self.vehicle_manager = VehicleManager(self.truck_repo)
        self.reconciler = WorldStateReconciliationService()

        self._wire_world_state(config)
        self._wire_common(auth)

    def _wire_memory(self) -> None:
        """Wire in-memory persistence implementations."""
        self.package_repo = InMemoryPackageRepository()
        self.customer_repo = InMemoryCustomerRepository()
        self.route_repo = InMemoryRouteRepository()
        self.truck_repo = InMemoryTruckRepository()
        self.unit_of_work = InMemoryUnitOfWork(
            routes=self.route_repo,
            packages=self.package_repo,
            trucks=self.truck_repo,
        )

    def _wire_postgres(self) -> None:
        """Wire PostgreSQL persistence implementations."""
        self.package_repo = PostgresPackageRepository()
        self.customer_repo = PostgresCustomerRepository()
        self.route_repo = PostgresRouteRepository()
        self.truck_repo = PostgresTruckRepository()
        self.unit_of_work = PostgresUnitOfWork()

    def _wire_world_state(self, config: AppConfig) -> None:
        """Wire world-state snapshot import/export for the active backend."""
        self.world_state_persistence = JsonWorldStatePersistence()

        if config.persistence_backend is PersistenceBackend.MEMORY:
            customer_repo = self.customer_repo
            package_repo = self.package_repo
            route_repo = self.route_repo

            if not isinstance(customer_repo, InMemoryCustomerRepository):
                raise TypeError("Memory world-state wiring requires InMemoryCustomerRepository.")
            if not isinstance(package_repo, InMemoryPackageRepository):
                raise TypeError("Memory world-state wiring requires InMemoryPackageRepository.")
            if not isinstance(route_repo, InMemoryRouteRepository):
                raise TypeError("Memory world-state wiring requires InMemoryRouteRepository.")

            self.world_state_runtime = InMemoryWorldStateRuntime(
                customer_repo=customer_repo,
                package_repo=package_repo,
                route_repo=route_repo,
                vehicle_manager=self.vehicle_manager,
            )
            self.world_state_snapshot_service = WorldStateSnapshotService(
                customer_repo=customer_repo,
                package_repo=package_repo,
                route_repo=route_repo,
                vehicle_manager=self.vehicle_manager,
                runtime_state=self.world_state_runtime,
                reconciler=self.reconciler,
            )
            self.world_state_gateway = InMemoryWorldStateGateway(
                snapshot_service=self.world_state_snapshot_service,
            )
            return

        self.world_state_gateway = UnsupportedWorldStateGateway(
            "JSON world-state import/export is not implemented for the Postgres backend yet."
        )
        self.world_state_runtime = None
        self.world_state_snapshot_service = None

    def _wire_common(self, auth: AuthService) -> None:
        """Wire services and use cases common to all persistence backends."""
        self.customer_service = CustomerService(self.customer_repo)
        self.auth = auth
        self.authz = AuthorizationService(auth.current_user)

        self.heartbeat_service = HeartbeatService(self.route_repo, self.reconciler, self.unit_of_work)
        self.advance_world_state_use_case = AdvanceWorldStateUseCase(self.heartbeat_service)

        self.save_world_state_use_case = SaveWorldStateUseCase(
            self.world_state_gateway,
            self.world_state_persistence,
        )
        self.load_world_state_use_case = LoadWorldStateUseCase(
            self.world_state_gateway,
            self.world_state_persistence,
        )
        self.default_world_state_path = str(get_json_config().state_path)

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
        self.remove_route_use_case = RemoveRouteUseCase(self.route_repo, self.unit_of_work)
        self.assign_truck_to_route_use_case = AssignTruckToRouteUseCase(
            self.route_repo, self.vehicle_manager, self.unit_of_work
        )
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


def build_container(auth: AuthService, config: AppConfig | None = None) -> Container:
    """Build the application container from explicit or environment config.

    Args:
        auth: Shared authentication service.
        config: Optional application configuration override.

    Returns:
        Fully wired application container.
    """
    return Container(auth=auth, config=config)
