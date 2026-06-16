from enum import StrEnum


class WorldStateStartupSkipReason(StrEnum):
    """Business reasons for skipping the restoration of the world state."""

    NO_SNAPSHOT_FOUND = "NO_SNAPSHOT_FOUND"
    SNAPSHOT_DISABLED = "SNAPSHOT_DISABLED"
