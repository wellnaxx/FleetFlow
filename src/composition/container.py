"""Application composition root for shared CLI and HTTP runtime dependencies."""

import logging
from datetime import datetime

from src.adapters.driven.persistence.database.repositories.audit_repository import PostgresAuditRepository
from src.adapters.driven.persistence.database.repositories.customer_repository import PostgresCustomerRepository
from src.adapters.driven.persistence.database.repositories.package_repository import PostgresPackageRepository
from src.adapters.driven.persistence.database.repositories.route_repository import PostgresRouteRepository
from src.adapters.driven.persistence.database.repositories.truck_repository import PostgresTruckRepository
from src.adapters.driven.persistence.database.unit_of_work import PostgresUnitOfWork
from src.adapters.driven.persistence.database.world_state_gateway import PostgresWorldStateGateway
from src.adapters.driven.persistence.database.world_state_importer import PostgresWorldStateImporter
from src.adapters.driven.persistence.json.config import get_json_config
from src.adapters.driven.persistence.json.world_state_persistence import JsonWorldStatePersistence
from src.adapters.driven.persistence.memory.audit_repository import InMemoryAuditRepository
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.adapters.driven.persistence.memory.truck_repository import InMemoryTruckRepository
from src.adapters.driven.persistence.memory.unit_of_work import InMemoryUnitOfWork
from src.adapters.driven.persistence.memory.world_state_gateway import (
    InMemoryWorldStateGateway,
    InMemoryWorldStateRuntime,
)
from src.application.eventing.collector import EventCollector
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
from src.application.services.customer_service import CustomerService
from src.application.services.heartbeat_service import HeartbeatService
from src.application.services.world_snapshot_validator import WorldStateSnapshotValidator
from src.application.services.world_state_linker import WorldStateSnapshotLinker
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder
from src.application.services.world_state_snapshot_preparer import WorldStateSnapshotPreparer
from src.application.services.world_state_snapshot_rebuilder import WorldStateSnapshotRebuilder
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
from src.application.use_cases.use_case_registry import (
    AuthUseCases,
    CustomerUseCases,
    PackageUseCases,
    RouteUseCases,
    StateUseCases,
    TruckUseCases,
)
from src.composition.config import AppConfig, PersistenceBackend, get_app_config
from src.composition.seed_fleet import seed_fleet_if_empty
from src.domain.services.vehicle_manager import VehicleManager
from src.ports.output.audit_repository import AuditRepositoryPort

logger = logging.getLogger(__name__)


class Container:
    """Wire repositories, services, use cases, and shared runtime services."""

    auth_cases: AuthUseCases
    customer_cases: CustomerUseCases
    package_cases: PackageUseCases
    route_cases: RouteUseCases
    truck_cases: TruckUseCases
    state_cases: StateUseCases

    def __init__(
        self,
        auth: AuthService,
        event_collector: EventCollector,
        config: AppConfig | None = None,
        audit_repository: AuditRepositoryPort | None = None,
    ) -> None:
        """Construct the application dependency graph.

        Args:
            auth: Shared authentication service used by auth-related use cases
                and authorization checks.
            event_collector: Shared event collector used by driving adapters to
                publish pending domain and application events after workflows
                complete successfully.
            config: Application configuration. When omitted, it is loaded from
                the environment.
            audit_repository: Optional repository instance shared with the
                audit event handler. When omitted, the container creates one
                for the configured persistence backend.
        """
        config = config or get_app_config()
        logger.info("Wiring application container for %s backend.", config.persistence_backend.value)

        self.event_collector = event_collector
        self._audit_repository = audit_repository

        if config.persistence_backend is PersistenceBackend.MEMORY:
            self._wire_memory()
            self.autosave_enabled = True
        elif config.persistence_backend is PersistenceBackend.POSTGRES:
            self._wire_postgres()
            self.autosave_enabled = False
        else:
            logger.critical("Unsupported persistence backend configured: %r.", config.persistence_backend)
            raise ValueError(f"Unsupported persistence backend: {config.persistence_backend!r}")

        seed_fleet_if_empty(self.truck_repo)
        self.vehicle_manager = VehicleManager(self.truck_repo)
        self.reconciler = WorldStateReconciliationService()
        self.builder = WorldStateSnapshotBuilder()
        self.validator = WorldStateSnapshotValidator(vehicle_manager=self.vehicle_manager)
        self.rebuilder = WorldStateSnapshotRebuilder()
        self.linker = WorldStateSnapshotLinker(vehicle_manager=self.vehicle_manager)
        self.preparer = WorldStateSnapshotPreparer(
            reconciler=self.reconciler,
            validator=self.validator,
            rebuilder=self.rebuilder,
            linker=self.linker,
        )

        self.clock = datetime.now
        self._wire_world_state(config)
        self._wire_services(auth)
        self._wire_use_cases()
        logger.info(
            "Application container wired with autosave=%s and default_world_state_path=%r.",
            self.autosave_enabled,
            self.default_world_state_path,
        )

    def _wire_memory(self) -> None:
        """Wire in-memory persistence implementations."""
        logger.info("Wiring in-memory persistence adapters.")
        self.package_repo = InMemoryPackageRepository()
        self.customer_repo = InMemoryCustomerRepository()
        self.route_repo = InMemoryRouteRepository()
        self.truck_repo = InMemoryTruckRepository()
        self.unit_of_work = InMemoryUnitOfWork(
            routes=self.route_repo,
            packages=self.package_repo,
            trucks=self.truck_repo,
        )
        self.audit_repo = self._audit_repository or InMemoryAuditRepository()

    def _wire_postgres(self) -> None:
        """Wire PostgreSQL persistence implementations."""
        logger.info("Wiring PostgreSQL persistence adapters.")
        self.package_repo = PostgresPackageRepository()
        self.customer_repo = PostgresCustomerRepository()
        self.route_repo = PostgresRouteRepository()
        self.truck_repo = PostgresTruckRepository()
        self.unit_of_work = PostgresUnitOfWork()
        self.audit_repo = self._audit_repository or PostgresAuditRepository()

    def _wire_world_state(self, config: AppConfig) -> None:
        """Wire world-state snapshot import/export for the active backend."""
        self.world_state_persistence = JsonWorldStatePersistence()

        if config.persistence_backend is PersistenceBackend.MEMORY:
            logger.info("Wiring in-memory world-state gateway.")
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
                preparer=self.preparer,
                builder=self.builder,
            )
            self.world_state_gateway = InMemoryWorldStateGateway(
                snapshot_service=self.world_state_snapshot_service,
            )
            return

        logger.info("Wiring PostgreSQL world-state import/export gateway.")
        self.world_state_gateway = PostgresWorldStateGateway(
            snapshot_builder=self.builder,
            snapshot_preparer=self.preparer,
            importer=PostgresWorldStateImporter(),
        )
        self.world_state_runtime = None
        self.world_state_snapshot_service = None

    def _wire_services(self, auth: AuthService) -> None:
        """Wire services common to all persistence backends."""
        logger.debug("Wiring application services.")
        self.customer_service = CustomerService(self.customer_repo)
        self.auth = auth
        self.authz = AuthorizationService(auth.current_user)
        self.heartbeat_service = HeartbeatService(self.route_repo, self.reconciler, self.unit_of_work)
        self.default_world_state_path = str(get_json_config().state_path)

    def _wire_use_cases(self) -> None:
        """Wire use cases common to all persistence backends."""
        logger.debug("Wiring application use cases.")
        self.auth_cases = AuthUseCases(
            login=LoginUseCase(self.auth, self.clock),
            logout=LogoutUseCase(self.auth.user_repository, self.auth, self.authz, self.clock),
            who_am_i=WhoAmIUseCase(self.auth),
            register_user=RegisterUserUseCase(self.auth, self.authz),
            change_password=ChangePasswordUseCase(self.auth, self.authz),
        )

        self.customer_cases = CustomerUseCases(
            view_all=ViewAllCustomersUseCase(self.customer_repo, self.authz),
        )

        self.package_cases = PackageUseCases(
            create=CreatePackageUseCase(self.customer_service, self.package_repo, self.authz),
            view=ViewPackageUseCase(self.package_repo, self.authz),
            view_all=ViewAllPackagesUseCase(self.package_repo, self.authz),
            remove=RemovePackageUseCase(self.package_repo, self.unit_of_work, self.authz, clock=self.clock),
            view_unassigned=ViewUnassignedPackagesUseCase(self.package_repo, self.authz),
        )

        self.route_cases = RouteUseCases(
            create=CreateRouteUseCase(self.route_repo, self.authz),
            view=ViewRouteUseCase(self.route_repo, self.authz),
            view_all=ViewAllRoutesUseCase(self.route_repo, self.authz),
            view_in_progress=ViewRoutesInProgressUseCase(self.route_repo, self.authz),
            remove=RemoveRouteUseCase(self.route_repo, self.unit_of_work, self.authz, clock=self.clock),
            assign_packages=AssignPackagesToRouteUseCase(
                self.route_repo, self.package_repo, self.authz, clock=self.clock
            ),
            assign_truck=AssignTruckToRouteUseCase(
                self.route_repo, self.vehicle_manager, self.unit_of_work, self.authz
            ),
            find_suitable_trucks=FindSuitableTrucksForRouteUseCase(
                self.route_repo, self.vehicle_manager, self.authz
            ),
            find_suitable_routes=FindSuitableRoutesForPackageUseCase(
                self.route_repo, self.package_repo, self.authz, clock=self.clock
            ),
        )
        self.truck_cases = TruckUseCases(
            view_all=ViewAllTrucksUseCase(self.vehicle_manager, self.authz),
        )
        self.state_cases = StateUseCases(
            advance=AdvanceWorldStateUseCase(self.heartbeat_service),
            save=SaveWorldStateUseCase(self.world_state_gateway, self.world_state_persistence, self.authz),
            load=LoadWorldStateUseCase(self.world_state_gateway, self.world_state_persistence, self.authz),
        )


def build_container(
    auth: AuthService,
    collector: EventCollector,
    config: AppConfig | None = None,
    audit_repository: AuditRepositoryPort | None = None,
) -> Container:
    """Build the application container from explicit or environment config.

    Args:
        auth: Shared authentication service.
        collector: Event collector shared by HTTP and CLI driving adapters.
        config: Optional application configuration override.
        audit_repository: Optional audit repository shared with event
            subscriptions.

    Returns:
        Fully wired application container.
    """
    return Container(auth=auth, event_collector=collector, config=config, audit_repository=audit_repository)
