"""Link detached domain objects rebuilt from world-state snapshots."""

from collections.abc import Mapping
from types import MappingProxyType

from src.adapters.driven.persistence.json.serialization import dt_from_str
from src.application.dto.candidate_truck_dto import CandidateTruckLink
from src.application.dto.linked_truck_state_dto import LinkedTruckState
from src.application.dto.rebuilt_world_dto import RebuiltWorld
from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import RouteSnapshot, TruckSnapshot, WorldStateSnapshot
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.ports.output.vehicle_manager import VehicleManagerPort


class WorldStateLinker:
    """Service for linking detached domain objects rebuilt from world-state snapshots."""

    def __init__(self, vehicle_manager: VehicleManagerPort) -> None:
        """Initialize linker dependencies.

        Args:
            vehicle_manager: Fleet service used to clone real trucks into candidate truck state.
        """
        self._vehicle_manager = vehicle_manager

    def link(self, snapshot: WorldStateSnapshot, rebuilt_world: RebuiltWorld) -> LinkedTruckState:
        """Restore package-route links and candidate truck-route links.

        Args:
            snapshot: Source snapshot containing relationship ids.
            rebuilt_world: Detached domain objects rebuilt from the snapshot.

        Returns:
            Candidate truck links needed after reconciliation to build runtime truck bindings.

        Raises:
            KeyError: If snapshot relationships reference missing rebuilt objects or fleet trucks.
            TypeError: If truck runtime fields contain invalid value types.
            ValueError: If truck runtime fields violate domain validation.
        """
        self._link_packages_to_routes(
            snapshots=snapshot.world.routes,
            rebuilt_packages=rebuilt_world.packages,
            rebuilt_routes=rebuilt_world.routes,
        )
        candidate_trucks_by_id = self._build_candidate_trucks(snapshot.world.trucks)
        truck_by_route_id = self._link_candidate_trucks_to_routes(
            route_snapshots=snapshot.world.routes,
            rebuilt_routes=rebuilt_world.routes,
            candidate_trucks_by_id=candidate_trucks_by_id,
        )
        return LinkedTruckState(
            trucks_by_route_id=MappingProxyType(truck_by_route_id),
            candidate_trucks_by_id=MappingProxyType(candidate_trucks_by_id),
        )

    def _link_packages_to_routes(
        self,
        snapshots: tuple[RouteSnapshot, ...],
        rebuilt_packages: Mapping[int, DeliveryPackage],
        rebuilt_routes: Mapping[int, DeliveryRoute],
    ) -> None:
        """Restore route package links on rebuilt route objects.

        Args:
            snapshots: Route snapshots containing package ids.
            rebuilt_packages: Rebuilt packages keyed by package id.
            rebuilt_routes: Rebuilt routes keyed by route id.

        Returns:
            None.

        Raises:
            KeyError: If a route or package id is missing from the rebuilt mappings.
        """
        for snapshot in snapshots:
            route = rebuilt_routes[snapshot.route_id]

            for package_id in snapshot.package_ids:
                package = rebuilt_packages[package_id]
                route.restore_package_link(package)

    def _link_candidate_trucks_to_routes(
        self,
        *,
        route_snapshots: tuple[RouteSnapshot, ...],
        rebuilt_routes: Mapping[int, DeliveryRoute],
        candidate_trucks_by_id: dict[int, CandidateTruckLink],
    ) -> dict[int, CandidateTruckLink]:
        """Restore candidate truck links on rebuilt route objects.

        Args:
            route_snapshots: Route snapshots containing assigned truck ids.
            rebuilt_routes: Rebuilt routes keyed by route id.
            candidate_trucks_by_id: Candidate truck links keyed by vehicle id.

        Returns:
            Candidate truck links keyed by assigned route id.

        Raises:
            KeyError: If a route or fleet truck id is missing.
        """
        real_trucks_by_id = {truck.vehicle_id: truck for truck in self._vehicle_manager.list_fleet()}
        links_by_route_id: dict[int, CandidateTruckLink] = {}

        for snapshot in route_snapshots:
            truck_vehicle_id = snapshot.truck_vehicle_id
            if truck_vehicle_id is None:
                continue

            route = rebuilt_routes[snapshot.route_id]
            link = candidate_trucks_by_id.get(truck_vehicle_id)
            if link is None:
                real_truck = real_trucks_by_id[truck_vehicle_id]
                candidate_truck = self._clone_truck(real_truck)
                candidate_truck.status = TruckStatus.FREE
                candidate_truck.current_location = route.start_location
                candidate_truck.busy_from = None
                candidate_truck.busy_until = None
                candidate_truck.in_transit_to = None
                candidate_truck.route = None
                link = CandidateTruckLink(real_truck=real_truck, candidate_truck=candidate_truck)
                candidate_trucks_by_id[truck_vehicle_id] = link

            link.candidate_truck.assign(route)
            route.truck = link.candidate_truck

            links_by_route_id[snapshot.route_id] = link

        return links_by_route_id

    def _build_candidate_trucks(
        self,
        snapshots: tuple[TruckSnapshot, ...],
    ) -> dict[int, CandidateTruckLink]:
        """Clone fleet trucks and apply snapshot runtime state to candidates.

        Args:
            snapshots: Truck snapshots containing persisted runtime state.

        Returns:
            Candidate truck links keyed by vehicle id.

        Raises:
            KeyError: If a truck snapshot references a missing fleet truck.
            TypeError: If datetime fields contain invalid value types.
            ValueError: If datetime fields violate serialization format.
        """
        real_trucks_by_id = {truck.vehicle_id: truck for truck in self._vehicle_manager.list_fleet()}
        candidates: dict[int, CandidateTruckLink] = {}

        for snapshot in snapshots:
            real_truck = real_trucks_by_id[snapshot.vehicle_id]
            candidate_truck = self._clone_truck(real_truck)

            candidate_truck.status = snapshot.status
            candidate_truck.current_location = snapshot.current_location
            candidate_truck.busy_from = dt_from_str(snapshot.busy_from)
            candidate_truck.busy_until = dt_from_str(snapshot.busy_until)
            candidate_truck.in_transit_to = snapshot.in_transit_to
            candidate_truck.route = None

            candidates[snapshot.vehicle_id] = CandidateTruckLink(
                real_truck=real_truck,
                candidate_truck=candidate_truck,
            )

        return candidates

    def build_truck_bindings(
        self,
        *,
        route_snapshots: tuple[RouteSnapshot, ...],
        routes: Mapping[int, DeliveryRoute],
        trucks_by_route_id: Mapping[int, CandidateTruckLink],
        candidate_trucks_by_id: Mapping[int, CandidateTruckLink],
    ) -> tuple[TruckBinding, ...]:
        """Build final truck bindings after candidate route reconciliation.

        Args:
            route_snapshots: Route snapshots containing assigned truck ids.
            routes: Rebuilt and reconciled routes keyed by route id.
            trucks_by_route_id: Candidate truck links keyed by assigned route id.
            candidate_trucks_by_id: Candidate truck links keyed by vehicle id.

        Returns:
            Truck bindings ordered by vehicle id.

        Raises:
            KeyError: If an assigned route id is missing from the link mappings.
        """
        bindings_by_truck_id: dict[int, TruckBinding] = {}

        for truck_id, link in candidate_trucks_by_id.items():
            candidate_truck = link.candidate_truck
            bindings_by_truck_id[truck_id] = TruckBinding(
                truck=link.real_truck,
                route=candidate_truck.route,
                status=candidate_truck.status,
                current_location=candidate_truck.current_location,
                busy_from=candidate_truck.busy_from,
                busy_until=candidate_truck.busy_until,
                in_transit_to=candidate_truck.in_transit_to,
            )

        for snapshot in route_snapshots:
            truck_vehicle_id = snapshot.truck_vehicle_id
            if truck_vehicle_id is None:
                continue

            link = trucks_by_route_id[snapshot.route_id]
            candidate_truck = link.candidate_truck
            route = routes[snapshot.route_id]
            bound_route = route if route.truck is candidate_truck else None

            if bound_route is None and truck_vehicle_id in bindings_by_truck_id:
                continue

            bindings_by_truck_id[truck_vehicle_id] = TruckBinding(
                truck=link.real_truck,
                route=bound_route,
                status=candidate_truck.status,
                current_location=candidate_truck.current_location,
                busy_from=candidate_truck.busy_from,
                busy_until=candidate_truck.busy_until,
                in_transit_to=candidate_truck.in_transit_to,
            )

        return tuple(bindings_by_truck_id[truck_id] for truck_id in sorted(bindings_by_truck_id))

    @staticmethod
    def _clone_truck(truck: Truck) -> Truck:
        """Clone static and runtime fields from a real truck.

        Args:
            truck: Fleet truck to clone.

        Returns:
            Detached truck copy with the same static and runtime fields.
        """
        clone = Truck(
            vehicle_id=truck.vehicle_id,
            name=truck.name,
            capacity=truck.capacity,
            max_range=truck.max_range,
        )
        clone.status = truck.status
        clone.current_location = truck.current_location
        clone.busy_from = truck.busy_from
        clone.busy_until = truck.busy_until
        clone.in_transit_to = truck.in_transit_to
        return clone
