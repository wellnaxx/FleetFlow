"""DTO for rolling back live truck runtime state after a failed swap."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True, slots=True)
class TruckRuntimeSnapshot:
    """Captured mutable truck fields used for runtime swap rollback."""

    truck: Truck
    status: TruckStatus
    current_location: LocationCode | None
    route: DeliveryRoute | None
    busy_from: datetime | None
    busy_until: datetime | None
    in_transit_to: LocationCode | None
