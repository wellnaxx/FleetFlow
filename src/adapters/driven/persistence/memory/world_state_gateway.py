from collections.abc import Mapping

from application.dto.truck_runtime_snapshot_dto import TruckRuntimeSnapshot
from src.adapters.driven.persistence.memory.customer_repository import InMemoryCustomerRepository
from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.adapters.driven.persistence.memory.route_repository import InMemoryRouteRepository
from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import CountersSnapshot, WorldStateSnapshot
from src.application.services.world_state_snapshot_service import WorldStateSnapshotService
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.services.vehicle_manager import VehicleManager
from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_runtime_port import WorldStateRuntimePort


class InMemoryWorldStateRuntime(WorldStateRuntimePort):
    """Apply snapshot swaps to the in-memory runtime collaborators."""

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

    def replace_world_state(
        self,
        *,
        customers_by_id: Mapping[int, Customer],
        packages_by_id: Mapping[int, DeliveryPackage],
        routes_by_id: Mapping[int, DeliveryRoute],
        counters: CountersSnapshot,
        truck_bindings: list[TruckBinding],
    ) -> None:
        previous_customers = {customer.customer_id: customer for customer in self._customer_repo.list_all()}
        previous_packages = {package.package_id: package for package in self._package_repo.list_all()}
        previous_routes = {route.route_id: route for route in self._route_repo.list_all()}
        previous_counters = CountersSnapshot(
            next_customer_id=self._customer_repo.peek_next_id(),
            next_package_id=self._package_repo.peek_next_id(),
            next_route_id=self._route_repo.peek_next_id(),
        )
        previous_trucks = self._snapshot_trucks()

        try:
            self._customer_repo.replace_customers(
                customers_by_id=customers_by_id,
                next_id=counters.next_customer_id,
            )
            self._package_repo.replace_packages(
                packages_by_id=packages_by_id,
                next_id=counters.next_package_id,
            )
            self._route_repo.replace_routes(
                routes_by_id=routes_by_id,
                next_id=counters.next_route_id,
            )
            self._vehicle_manager.replace_truck_bindings(bindings=truck_bindings)
        except Exception:
            self._customer_repo.replace_customers(
                customers_by_id=previous_customers,
                next_id=previous_counters.next_customer_id,
            )
            self._package_repo.replace_packages(
                packages_by_id=previous_packages,
                next_id=previous_counters.next_package_id,
            )
            self._route_repo.replace_routes(
                routes_by_id=previous_routes,
                next_id=previous_counters.next_route_id,
            )
            self._restore_trucks(previous_trucks)
            raise

    def _snapshot_trucks(self) -> list[TruckRuntimeSnapshot]:
        return [
            TruckRuntimeSnapshot(
                truck=truck,
                status=truck.status,
                current_location=truck.current_location,
                route=truck.route,
                busy_from=truck.busy_from,
                busy_until=truck.busy_until,
                in_transit_to=truck.in_transit_to,
            )
            for truck in self._vehicle_manager.list_fleet()
        ]

    def _restore_trucks(self, snapshots: list[TruckRuntimeSnapshot]) -> None:
        for snapshot in snapshots:
            snapshot.truck.status = snapshot.status
            snapshot.truck.current_location = snapshot.current_location
            snapshot.truck.route = snapshot.route
            snapshot.truck.busy_from = snapshot.busy_from
            snapshot.truck.busy_until = snapshot.busy_until
            snapshot.truck.in_transit_to = snapshot.in_transit_to


class InMemoryWorldStateGateway(WorldStateGatewayPort):
    """Bridge world-state snapshot use cases to the in-memory runtime."""

    def __init__(self, snapshot_service: WorldStateSnapshotService) -> None:
        """Initialize the gateway with the snapshot orchestration service.

        Args:
            snapshot_service: Service used to build and apply snapshots.
        """
        self._snapshot_service = snapshot_service

    def build_snapshot(self) -> WorldStateSnapshot:
        """Build a snapshot from the current in-memory runtime state."""
        return self._snapshot_service.build_snapshot()

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        """Replace in-memory runtime state from a snapshot payload."""
        self._snapshot_service.apply_snapshot(snapshot)
