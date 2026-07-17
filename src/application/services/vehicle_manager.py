"""Application service for fleet access, suitability, and runtime bindings."""

from collections.abc import Sequence

from src.application.dto.truck_binding_dto import TruckBinding
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.truck_assignment_policy import RouteSuitabilityView, TruckAssignmentPolicy
from src.ports.output.truck_repository import TruckRepositoryPort


class VehicleManager:
    """Coordinate fleet persistence and pure truck assignment decisions."""

    def __init__(self, truck_repo: TruckRepositoryPort) -> None:
        """Initialize the fleet service.

        Args:
            truck_repo: Repository used to query and persist truck state.
        """
        self._truck_repo = truck_repo

    def list_fleet(self) -> list[Truck]:
        """Return all trucks supplied by the fleet repository.

        Returns:
            Trucks currently managed by the fleet service.
        """
        return self._truck_repo.list_fleet()

    def find_by_id(self, vehicle_id: int) -> Truck | None:
        """Return a truck by vehicle id, if it exists.

        Args:
            vehicle_id: Truck identifier to look up.

        Returns:
            Matching truck, or None when no truck exists.
        """
        return self._truck_repo.find_by_id(vehicle_id)

    def is_suitable_for_route(self, truck: Truck, route: RouteSuitabilityView) -> tuple[bool, str]:
        """Check structural and schedule suitability for assigning a truck.

        Args:
            truck: Candidate truck.
            route: Route view used for segment capacity, range, location, and
                timing checks.

        Returns:
            Pair of suitability flag and failure reason. The reason is empty
            when the truck is suitable.
        """
        decision = TruckAssignmentPolicy.evaluate(truck=truck, route=route)
        return decision.accepted, decision.message or ""

    def find_available_for_route(self, route: DeliveryRoute) -> list[Truck]:
        """Return trucks that can serve a route, ordered by vehicle id.

        Args:
            route: Route needing a truck.

        Returns:
            Suitable trucks sorted by vehicle id.
        """
        trucks = [
            truck
            for truck in self._truck_repo.list_fleet()
            if TruckAssignmentPolicy.evaluate(
                truck=truck,
                route=route,
            ).accepted
        ]
        return sorted(trucks, key=lambda truck: truck.vehicle_id)

    def replace_truck_bindings(self, bindings: Sequence[TruckBinding]) -> None:
        """Replace runtime truck assignment state from prepared bindings.

        Existing assignment state is cleared and persisted before each
        prepared binding is applied. A bound route receives the corresponding
        truck backlink.

        Args:
            bindings: Prepared truck state produced by snapshot reconciliation.

        Returns:
            None.

        Raises:
            AssertionError: If an existing truck-to-route reference does not
                have the matching route-to-truck backlink.
        """
        for truck in self._truck_repo.list_fleet():
            existing_route = truck.route
            if existing_route is not None:
                assert existing_route.truck is truck, (
                    "Truck and route assignment backlinks must be consistent before replacement."
                )
                existing_route.truck = None

            truck.route = None
            truck.status = TruckStatus.FREE
            truck.busy_from = None
            truck.busy_until = None
            truck.in_transit_to = None
            self._truck_repo.update_state(truck)

        for binding in bindings:
            truck = binding.truck
            route = binding.route

            truck.status = binding.status
            truck.current_location = binding.current_location
            truck.busy_from = binding.busy_from
            truck.busy_until = binding.busy_until
            truck.in_transit_to = binding.in_transit_to
            truck.route = route
            if route is not None:
                route.truck = truck

            self._truck_repo.update_state(truck)
