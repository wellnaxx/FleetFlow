from dataclasses import dataclass

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class TruckBinding:
    truck: Truck
    route: DeliveryRoute
