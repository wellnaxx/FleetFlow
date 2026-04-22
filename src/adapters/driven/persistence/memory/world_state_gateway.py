from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot
from src.application.services.world_state_snapshot_service import WorldStateSnapshotService
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.services.vehicle_manager import VehicleManager
from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_runtime_port import WorldStateRuntimePort


class _InMemoryWorldStateRuntime(WorldStateRuntimePort):
    def __init__(
        self,
        customer_repo: InMemoryCustomerRepository,
        package_repo: InMemoryPackageRepository,
        route_repo: InMemoryRouteRepository,
        vehicle_manager: VehicleManager,
    ) -> None:
        self._customer_repo = customer_repo
        self._package_repo = package_repo
        self._route_repo = route_repo
        self._vehicle_manager = vehicle_manager

    def replace_customers(self, customers_by_id: dict[int, Customer], next_id: int) -> None:
        self._customer_repo.replace_customers(customers_by_id, next_id)

    def replace_packages(self, packages_by_id: dict[int, DeliveryPackage], next_id: int) -> None:
        self._package_repo.replace_packages(packages_by_id, next_id)

    def replace_routes(self, routes_by_id: dict[int, DeliveryRoute], next_id: int) -> None:
        self._route_repo.replace_routes(routes_by_id, next_id)

    def replace_truck_bindings(self, bindings: list[TruckBinding]) -> None:
        self._vehicle_manager.replace_truck_bindings(bindings)


class InMemoryWorldStateGateway(WorldStateGatewayPort):
    def __init__(
        self,
        customer_repo: InMemoryCustomerRepository,
        package_repo: InMemoryPackageRepository,
        route_repo: InMemoryRouteRepository,
        vehicle_manager: VehicleManager,
        snapshot_service: WorldStateSnapshotService | None = None,
    ) -> None:
        runtime_state = _InMemoryWorldStateRuntime(
            customer_repo=customer_repo,
            package_repo=package_repo,
            route_repo=route_repo,
            vehicle_manager=vehicle_manager,
        )
        self._snapshot_service = snapshot_service or WorldStateSnapshotService(
            customer_repo=customer_repo,
            package_repo=package_repo,
            route_repo=route_repo,
            vehicle_manager=vehicle_manager,
            runtime_state=runtime_state,
        )

    def build_snapshot(self) -> WorldStateSnapshot:
        return self._snapshot_service.build_snapshot()

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        self._snapshot_service.apply_snapshot(snapshot)
