from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.map import Map

if TYPE_CHECKING:
    from datetime import datetime

    from src.models.customer import Customer
    from src.models.delivery_route import DeliveryRoute


class DeliveryPackage:
    _next_id: int = 1

    def __init__(
        self,
        start_location: str,
        end_location: str,
        weight: float,
        customer: Customer,
        package_id: int | None = None,
    ) -> None:
        if not Map.is_valid_location(start_location):
            raise ValueError(f"Invalid start location: {start_location}")
        if not Map.is_valid_location(end_location):
            raise ValueError(f"Invalid end location: {end_location}")
        if start_location == end_location:
            raise ValueError("Start and end locations must be different.")
        if float(weight) <= 0:
            raise ValueError("Weight must be positive.")
        if package_id is None:
            package_id = DeliveryPackage._next_id
            DeliveryPackage._next_id += 1
        self._package_id: int = package_id
        self.start_location: str = start_location
        self.end_location: str = end_location
        self.current_location: str = start_location
        self.weight: float = float(weight)
        self.customer: Customer | None = customer

        self.route: DeliveryRoute | None = None
        self.expected_arrival: datetime | None = None
        self.status: str | None = None

    @property
    def package_id(self) -> int:
        return self._package_id

    def _set_package_id(self, value: int) -> None:
        self._package_id = value

    def info(self) -> str:
        """Return a human-readable description of the package."""
        if self.customer is not None:
            cname = self.customer.name
            cemail = self.customer.contact.display_email()
            cphone = self.customer.contact.display_phone()
            contact_info = f"{cname} ({cemail}, {cphone})"
        else:
            contact_info = "No customer"
        route_str = self.route.route_id if self.route else "Not assigned"
        if self.expected_arrival:
            arrival_str = self.expected_arrival.strftime("%Y-%m-%d %H:%M")
        else:
            arrival_str = "Not assigned"
        return (
            f"Package {self.package_id}: "
            f"{self.start_location} → {self.end_location}, {self.weight:.1f}kg\n"
            f"Customer: {contact_info}\n"
            f"Assigned route: {route_str}\n"
            f"Expected arrival: {arrival_str}"
        )
