"""Result model for package-to-route suitability searches."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.value_objects.location_code import LocationCode


@dataclass
class SuitableRouteForPackage:
    """Route option that can carry a package."""

    route_id: int
    start_location: LocationCode
    end_location: LocationCode
    eta: datetime | None
    capacity_left: float | None
    end_city: LocationCode
