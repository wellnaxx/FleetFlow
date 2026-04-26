"""Delivery package entity and assignment state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.enums.item_status import ItemStatus
from src.domain.services.map import Map
from src.domain.value_objects.location_code import LocationCode, location_code_or_none

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.entities.customer import Customer
    from src.domain.entities.delivery_route import DeliveryRoute


class DeliveryPackage:
    """Package shipment tracked from pickup to delivery."""

    def __init__(
        self,
        start_location: LocationCode,
        end_location: LocationCode,
        weight: float,
        customer: Customer,
        package_id: int,
    ) -> None:
        """Create a package shipment.

        Args:
            start_location: Pickup location code.
            end_location: Delivery location code.
            weight: Package weight in kilograms.
            customer: Owning customer.
            package_id: Stable package identifier.

        Raises:
            ValueError: If locations are invalid, equal, or the weight is not
                positive.
        """
        start_location = LocationCode(start_location)
        end_location = LocationCode(end_location)
        if not Map.is_valid_location(start_location):
            raise ValueError(f"Invalid start location: {start_location}")
        if not Map.is_valid_location(end_location):
            raise ValueError(f"Invalid end location: {end_location}")
        if start_location == end_location:
            raise ValueError("Start and end locations must be different.")
        if float(weight) <= 0:
            raise ValueError("Weight must be positive.")
        self._package_id: int = package_id
        self.start_location: LocationCode = start_location
        self.end_location: LocationCode = end_location
        self._current_location: LocationCode | None = self.start_location
        self.weight: float = float(weight)
        self.customer: Customer = customer

        self.route: DeliveryRoute | None = None
        self.expected_arrival: datetime | None = None
        self.status: ItemStatus = ItemStatus.TODO

    @property
    def package_id(self) -> int:
        """Stable package identifier."""
        return self._package_id

    @property
    def current_location(self) -> LocationCode:
        """Current package location."""
        location = self._current_location
        if location is None:
            return self.start_location
        return location

    @current_location.setter
    def current_location(self, value: LocationCode | None) -> None:
        self._current_location = location_code_or_none(value)

    def reset_assignment_state(self) -> None:
        """Clear route-derived state and return the package to the unassigned baseline."""
        self.route = None
        self.expected_arrival = None
        self.status = ItemStatus.TODO
        self.current_location = self.start_location

    def info(self) -> str:
        """Return a human-readable description of the package.

        Returns:
            Multi-line package summary for CLI display.
        """
        cname = self.customer.name
        cemail = self.customer.contact.display_email()
        cphone = self.customer.contact.display_phone()
        contact_info = f"{cname} ({cemail}, {cphone})"
        route_str = self.route.route_id if self.route else "Not assigned"
        if self.expected_arrival:
            arrival_str = self.expected_arrival.strftime("%Y-%m-%d %H:%M")
        else:
            arrival_str = "Not assigned"
        return (
            f"Package {self.package_id}: "
            f"{self.start_location} -> {self.end_location}, {self.weight:.1f}kg\n"
            f"Customer: {contact_info}\n"
            f"Assigned route: {route_str}\n"
            f"Expected arrival: {arrival_str}"
        )
