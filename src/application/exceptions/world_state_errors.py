"""World-state persistence and loading exception types."""

from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.application_errors import ApplicationError


class WorldStateError(ApplicationError):
    """Base class for world-state persistence and loading failures."""


class WorldStateFileNotFoundError(WorldStateError):
    """Raised when a requested world-state file does not exist."""


class WorldStateCorruptionError(WorldStateError):
    """Raised when a world-state file exists but cannot be parsed or validated."""

    def __init__(self, message: str, *, reason: WorldStateCorruptionReason) -> None:
        super().__init__(message)
        self.reason = reason


class WorldStatePersistenceError(WorldStateError):
    """Raised when world-state I/O fails for reasons other than missing/corrupt data."""


class WorldStateRuntimeSwapError(WorldStateError):
    """Raised when a valid world-state snapshot cannot be committed to runtime."""
