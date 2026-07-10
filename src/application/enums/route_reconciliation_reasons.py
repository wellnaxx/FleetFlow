"""Reasons for repairing route status during schedule reconciliation."""

from enum import StrEnum


class RouteReconciliationReason(StrEnum):
    """Explain why reconciliation directly corrected a route status.

    Normal forward transitions into progress or completion use domain events.
    These reasons cover schedule-derived corrections that bypass those
    lifecycle methods.
    """

    MISSING_DEPARTURE_TIME = "missing_departure_time"
    MISSING_EXPECTED_COMPLETION_TIME = "missing_expected_completion_time"
    BEFORE_SCHEDULED_DEPARTURE = "before_scheduled_departure"
