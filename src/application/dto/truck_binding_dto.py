from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class TruckBinding:
    truck: Truck
    route: DeliveryRoute | None
    status: str
    current_location: str | None
    busy_from: datetime | None
    busy_until: datetime | None
    in_transit_to: str | None
