"""DTO for applying prepared truck state to the live fleet."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class TruckBinding:
    """Prepared runtime state for one real truck."""

    truck: Truck
    route: DeliveryRoute | None
    status: str
    current_location: str | None
    busy_from: datetime | None
    busy_until: datetime | None
    in_transit_to: str | None
