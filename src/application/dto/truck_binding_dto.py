"""DTO for applying prepared truck state to the live fleet."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True)
class TruckBinding:
    """Prepared runtime state for one real truck."""

    truck: Truck
    route: DeliveryRoute | None
    status: TruckStatus
    current_location: LocationCode | None
    busy_from: datetime | None
    busy_until: datetime | None
    in_transit_to: LocationCode | None
