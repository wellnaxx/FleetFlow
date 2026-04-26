"""DTO for rolling back live truck runtime state after a failed swap."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class TruckRuntimeSnapshot:
    """Captured mutable truck fields used for runtime swap rollback."""

    truck: Truck
    status: str
    current_location: str | None
    route: DeliveryRoute | None
    busy_from: datetime | None
    busy_until: datetime | None
    in_transit_to: str | None
