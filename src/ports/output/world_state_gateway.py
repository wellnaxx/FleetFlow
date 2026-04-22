from typing import Protocol

from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot


class WorldStateGatewayPort(Protocol):
    def build_snapshot(self) -> WorldStateSnapshot: ...
    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None: ...
