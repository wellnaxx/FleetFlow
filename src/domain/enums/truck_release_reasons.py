from enum import StrEnum


class TruckReleaseReason(StrEnum):
    """Reasons for releasing a truck from a delivery route."""

    ROUTE_COMPLETED = "ROUTE_COMPLETED"
    ROUTE_REMOVED = "ROUTE_REMOVED"
