"""Output port for world-state persistence adapters."""

from typing import Protocol

from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot


class WorldStatePersistencePort(Protocol):
    """Persist and restore serialized world-state snapshots."""

    def write(self, path: str, snapshot: WorldStateSnapshot) -> str:
        """Write a snapshot and return the resolved absolute path.

        Args:
            path: Target path requested by the caller.
            snapshot: Snapshot payload to serialize.

        Returns:
            Absolute path written by the adapter.
        """
        ...

    def read(self, path: str) -> tuple[str, WorldStateSnapshot]:
        """Read a snapshot and return the resolved absolute path.

        Args:
            path: Source path requested by the caller.

        Returns:
            A tuple of resolved absolute path and parsed snapshot.

        Raises:
            WorldStateError: If the file is missing, corrupt, or unreadable.
        """
        ...
