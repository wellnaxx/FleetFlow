"""Fleet inventory and truck suitability service."""

from collections.abc import Sequence

from src.application.dto.truck_binding_dto import TruckBinding
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.ports.output.truck_repository import TruckRepositoryPort
from src.ports.output.vehicle_manager import RouteSuitabilityView


class VehicleManager:
    """Manage fleet vehicles, availability checks, and snapshot binding restore."""

    def __init__(self, truck_repo: TruckRepositoryPort) -> None:
        self._truck_repo = truck_repo

    def list_fleet(self) -> list[Truck]:
        """Return the fleet as a copy of the manager's vehicle list.

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
        if truck.max_range < route.total_distance_km:
            return False, "range too short"
        if truck.capacity < route.maximum_segment_load():
            return False, "insufficient capacity"
        if truck.current_location != route.start_location:
            return False, f"wrong location ({truck.current_location} != {route.start_location})"
        if truck.route is not None:
            if route.departure_time is None:
                return False, "route not scheduled yet"

            current_eta = truck.route.eta_final
            if current_eta is None:
                return False, "truck already assigned to a route with unknown availability"

            if current_eta >= route.departure_time:
                return False, "truck busy in the requested time window"

        return True, ""

    def find_available_for_route(self, route: DeliveryRoute) -> list[Truck]:
        """Return trucks that can serve a route, ordered by vehicle id.

        Args:
            route: Route needing a truck.

        Returns:
            Suitable trucks sorted by vehicle id.
        """
        result: list[Truck] = []
        for truck in self._truck_repo.list_fleet():
            ok, _ = self.is_suitable_for_route(truck, route)
            if ok:
                result.append(truck)
        result.sort(key=lambda truck: truck.vehicle_id)
        return result

    def replace_truck_bindings(self, bindings: Sequence[TruckBinding]) -> None:
        """Replace runtime truck assignment state from prepared bindings.

        Args:
            bindings: Prepared truck state produced by snapshot reconciliation.
        """
        for truck in self._truck_repo.list_fleet():
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
