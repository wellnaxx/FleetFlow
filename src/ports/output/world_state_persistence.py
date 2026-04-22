from typing import Protocol

from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot


class WorldStatePersistencePort(Protocol):
    def write(self, path: str, snapshot: WorldStateSnapshot) -> str: ...
    def read(self, path: str) -> tuple[str, WorldStateSnapshot]: ...
