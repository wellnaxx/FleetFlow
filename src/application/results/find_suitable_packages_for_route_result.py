from dataclasses import dataclass
from datetime import datetime


@dataclass
class SuitableRouteForPackage:
    route_id: int
    start_location: str
    end_location: str
    eta: datetime | None
    capacity_left: float | None
    end_city: str
