from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class LoadWorldStateUseCase:
    def __init__(
        self,
        world_state_gateway: WorldStateGatewayPort,
        persistence: WorldStatePersistencePort,
    ) -> None:
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence

    def execute(self, path: str) -> str:
        abs_path, snapshot = self._persistence.read(path)
        self._world_state_gateway.apply_snapshot(snapshot)
        return abs_path
