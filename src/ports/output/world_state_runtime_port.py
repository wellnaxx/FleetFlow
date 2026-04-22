from typing import Protocol

from src.application.dto.truck_binding_dto import TruckBinding
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


class WorldStateRuntimePort(Protocol):
    """Replace the mutable in-memory runtime state during snapshot loads."""

    def replace_customers(self, customers_by_id: dict[int, Customer], next_id: int) -> None:
        """Replace customer state and its next-id counter."""
        ...

    def replace_packages(self, packages_by_id: dict[int, DeliveryPackage], next_id: int) -> None:
        """Replace package state and its next-id counter."""
        ...

    def replace_routes(self, routes_by_id: dict[int, DeliveryRoute], next_id: int) -> None:
        """Replace route state and its next-id counter."""
        ...

    def replace_truck_bindings(self, bindings: list[TruckBinding]) -> None:
        """Replace live truck-to-route assignments."""
        ...
