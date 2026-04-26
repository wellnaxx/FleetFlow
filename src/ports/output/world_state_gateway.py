"""Output port for runtime world-state snapshot gateways."""

from typing import Protocol

from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot


class WorldStateGatewayPort(Protocol):
    """Build and apply world-state snapshots for the live runtime."""

    def build_snapshot(self) -> WorldStateSnapshot:
        """Build a snapshot from the active runtime state.

        Returns:
            Snapshot DTO representing current world state.
        """
        ...

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        """Replace the active runtime state using a snapshot payload.

        Args:
            snapshot: Validated or raw world-state snapshot to apply.

        Raises:
            WorldStateError: If the snapshot cannot be prepared or committed.
        """
        ...
