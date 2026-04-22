from typing import Protocol

from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot


class WorldStateGatewayPort(Protocol):
    """Build and apply world-state snapshots for the live runtime."""

    def build_snapshot(self) -> WorldStateSnapshot:
        """Build a snapshot from the active runtime state."""
        ...

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        """Replace the active runtime state using a snapshot payload."""
        ...
