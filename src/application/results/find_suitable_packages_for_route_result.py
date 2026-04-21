from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute


@dataclass
class SuitableRouteForPackage:
    route: DeliveryRoute
    eta: datetime | None
    capacity_left: float | None
    end_city: str
