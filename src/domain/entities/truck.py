"""Truck entity and route assignment state."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.domain.enums.truck_status import TruckStatus

if TYPE_CHECKING:
    from src.domain.entities.delivery_route import DeliveryRoute


class Truck:
    """Fleet vehicle with capacity, range, location, and assignment state."""

    def __init__(self, vehicle_id: int, name: str, capacity: int, max_range: int) -> None:
        """Create a fleet truck.

        Args:
            vehicle_id: Stable fleet vehicle id.
            name: Supported truck model name.
            capacity: Maximum cargo capacity in kilograms.
            max_range: Maximum route distance in kilometers.

        Raises:
            ValueError: If the truck model name is unsupported.
        """
        if name not in ("Scania", "Man", "Actros"):
            raise ValueError("Truck name must be Scania, Man or Actros")
        self.vehicle_id: int = vehicle_id
        self.name: str = name
        self.capacity: int = int(capacity)
        self.max_range: int = int(max_range)
        self.status: str = TruckStatus.FREE
        self.current_location: str | None = None
        self.route: DeliveryRoute | None = None
        self.busy_from: datetime | None = None
        self.busy_until: datetime | None = None
        self.in_transit_to: str | None = None

    def is_free(self) -> bool:
        """Return whether the truck is available for assignment.

        Returns:
            True when the truck status is free.
        """
        return self.status == TruckStatus.FREE

    def assign(self, route: DeliveryRoute) -> None:
        """Record the assignment window.

        Args:
            route: Route assigned to this truck.
        """
        self.route = route
        self.status = TruckStatus.ON_THE_WAY
        self.busy_from = route.departure_time
        self.busy_until = route.eta_final
        self.in_transit_to = None

    def release(self, *, now: datetime | None = None, force: bool = False) -> bool:
        """Finish the current route and mark the truck free.

        Args:
            now: Time used to decide whether the truck has reached the final ETA.
            force: When true, release immediately regardless of ETA.

        Returns:
            True when an assigned route was released; false when no release
            occurred.
        """
        if self.route is None:
            self.status = TruckStatus.FREE
            self.in_transit_to = None
            self.busy_from = None
            self.busy_until = None
            return False

        if not force:
            now = now or datetime.now()
            eta = self.route.eta_final
            if eta is None or now < eta:
                return False

        end_city = self.route.end_location
        if end_city:
            self.current_location = end_city

        self.route = None
        self.status = TruckStatus.FREE
        self.in_transit_to = None
        self.busy_from = None
        self.busy_until = None
        return True

    def info(self) -> str:
        """Return a human-readable truck summary.

        Returns:
            Multi-line truck summary for CLI display.
        """
        return (
            f"Vehicle ID: {self.vehicle_id}\n"
            f"Name: {self.name}\n"
            f"Capacity: {self.capacity}\n"
            f"Max range: {self.max_range}\n"
            f"Status: {self.status}\n"
            f"Location: {self.current_location or 'Unknown'}"
        )
