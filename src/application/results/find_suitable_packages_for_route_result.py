"""Result model for package-to-route suitability searches."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SuitableRouteForPackage:
    """Route option that can carry a package."""

    route_id: int
    start_location: str
    end_location: str
    eta: datetime | None
    capacity_left: float | None
    end_city: str
