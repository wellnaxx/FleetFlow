from datetime import datetime
from typing import Protocol

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


class RouteSuitabilityView(Protocol):
    """Describe the route fields needed for truck suitability checks."""

    @property
    def total_distance_km(self) -> int: ...

    @property
    def start_location(self) -> str: ...

    @property
    def departure_time(self) -> datetime | None: ...

    def total_assigned_weight(self) -> float: ...


class VehicleManagerPort(Protocol):
    """Manage truck availability and route suitability decisions."""

    def list_fleet(self) -> list[Truck]: ...
    def find_by_id(self, vehicle_id: int) -> Truck | None: ...
    def is_suitable_for_route(self, truck: Truck, route: RouteSuitabilityView) -> tuple[bool, str]: ...
    def find_available_for_route(self, route: DeliveryRoute) -> list[Truck]: ...
