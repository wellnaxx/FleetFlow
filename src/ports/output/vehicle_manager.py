"""Output port for fleet and truck suitability services."""

from datetime import datetime
from typing import Protocol

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


class RouteSuitabilityView(Protocol):
    """Describe the route fields needed for truck suitability checks."""

    @property
    def total_distance_km(self) -> int:
        """Total route distance in kilometers."""
        ...

    @property
    def start_location(self) -> str:
        """Route origin location."""
        ...

    @property
    def departure_time(self) -> datetime | None:
        """Scheduled route departure time, if scheduled."""
        ...

    def total_assigned_weight(self) -> float:
        """Return total package weight currently assigned to the route."""
        ...


class VehicleManagerPort(Protocol):
    """Manage truck availability and route suitability decisions."""

    def list_fleet(self) -> list[Truck]:
        """Return all fleet trucks."""
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
        """Return free trucks suitable for a route.

        Args:
            route: Route that needs a truck.

        Returns:
            Suitable free trucks.
        """
        ...
