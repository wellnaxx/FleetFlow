"""Package item status values."""

from enum import StrEnum


class ItemStatus(StrEnum):
    """Lifecycle status for a delivery package."""

    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
