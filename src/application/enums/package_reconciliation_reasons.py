"""Reasons for repairing package state during route reconciliation."""

from enum import StrEnum


class PackageReconciliationReason(StrEnum):
    """Explain why reconciliation directly corrected package state.

    Ordinary pickup and delivery transitions retain their domain events.
    These reasons describe schedule-derived updates or repairs that cannot be
    represented by those normal lifecycle transitions.
    """

    ROUTE_UNSCHEDULED = "route_unscheduled"
    ROUTE_PATH_INVALID = "route_path_invalid"
    BEFORE_SCHEDULED_PICKUP = "before_scheduled_pickup"
    MISSING_PICKUP_TIME = "missing_pickup_time"
    LIFECYCLE_STATE_INCONSISTENT = "lifecycle_state_inconsistent"
    ROUTE_PROGRESS_ADVANCED = "route_progress_advanced"
    EXPECTED_ARRIVAL_RECALCULATED = "expected_arrival_recalculated"
