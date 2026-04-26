"""Route lifecycle status values."""

from enum import StrEnum


class RouteStatus(StrEnum):
    """Lifecycle status for a delivery route."""

    PLANNED = "PLANNED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
