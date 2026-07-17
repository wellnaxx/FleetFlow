"""Application boundary for fleet access and truck assignment operations."""

from collections.abc import Sequence
from typing import Protocol

from src.application.dto.truck_binding_dto import TruckBinding
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.services.truck_assignment_policy import RouteSuitabilityView


class VehicleManagerPort(Protocol):
    """Manage truck availability, suitability, and restored runtime state."""

    def list_fleet(self) -> list[Truck]:
        """Return all fleet trucks.

        Returns:
            Trucks supplied by the underlying fleet repository.
        """
        ...

    def find_by_id(self, vehicle_id: int) -> Truck | None:
        """Return a truck by vehicle id, or `None` when absent.

        Args:
            vehicle_id: Fleet vehicle id to look up.

        Returns:
            Matching truck, or `None`.
        """
        ...

    def is_suitable_for_route(self, truck: Truck, route: RouteSuitabilityView) -> tuple[bool, str]:
        """Return whether a truck can serve a route and the reason.

        Args:
            truck: Truck to evaluate.
            route: Route-shaped object with suitability fields.

        Returns:
            Tuple of suitability flag and human-readable reason.
        """
        ...

    def find_available_for_route(self, route: DeliveryRoute) -> list[Truck]:
        """Return trucks whose assignment policy accepts a route.

        Args:
            route: Route that needs a truck.

        Returns:
            Suitable trucks ordered by the service implementation.
        """
        ...

    def replace_truck_bindings(self, bindings: Sequence[TruckBinding]) -> None:
        """Replace mutable truck state from prepared snapshot bindings.

        Args:
            bindings: Prepared state for trucks in the live fleet.

        Returns:
            None.
        """
        ...
