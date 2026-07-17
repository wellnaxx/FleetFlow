"""Normalized reasons why truck assignment policy rejects a candidate."""

from enum import StrEnum


class TruckAssignmentRejectionReason(StrEnum):
    """Machine-readable truck-to-route assignment rejection categories."""

    TRUCK_RANGE_INSUFFICIENT = "TRUCK_RANGE_INSUFFICIENT"
    TRUCK_CAPACITY_INSUFFICIENT = "TRUCK_CAPACITY_INSUFFICIENT"
    TRUCK_AT_WRONG_LOCATION = "TRUCK_AT_WRONG_LOCATION"
    TARGET_ROUTE_UNSCHEDULED = "TARGET_ROUTE_UNSCHEDULED"
    CURRENT_ROUTE_AVAILABILITY_UNKNOWN = "CURRENT_ROUTE_AVAILABILITY_UNKNOWN"
    AVAILABILITY_WINDOW_OVERLAP = "AVAILABILITY_WINDOW_OVERLAP"
