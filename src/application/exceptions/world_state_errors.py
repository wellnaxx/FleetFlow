from src.application.exceptions.application_errors import ApplicationError


class WorldStateError(ApplicationError):
    """Base class for world-state persistence and loading failures."""


class WorldStateFileNotFoundError(WorldStateError):
    """Raised when a requested world-state file does not exist."""


class WorldStateCorruptionError(WorldStateError):
    """Raised when a world-state file exists but cannot be parsed or validated."""


class WorldStatePersistenceError(WorldStateError):
    """Raised when world-state I/O fails for reasons other than missing/corrupt data."""


class WorldStateRuntimeSwapError(WorldStateError):
    """Raised when a valid world-state snapshot cannot be committed to runtime."""
