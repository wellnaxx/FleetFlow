from typing import Protocol

from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot


class WorldStatePersistencePort(Protocol):
    """Persist and restore serialized world-state snapshots."""

    def write(self, path: str, snapshot: WorldStateSnapshot) -> str:
        """Write a snapshot and return the resolved absolute path."""
        ...

    def read(self, path: str) -> tuple[str, WorldStateSnapshot]:
        """Read a snapshot and return the resolved absolute path.

        Raises world-state exceptions for missing, corrupt, or unreadable files.
        """
        ...
