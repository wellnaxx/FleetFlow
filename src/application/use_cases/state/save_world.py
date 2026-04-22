from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class SaveWorldStateUseCase:
    def __init__(
        self,
        world_state_gateway: WorldStateGatewayPort,
        persistence: WorldStatePersistencePort,
    ) -> None:
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence

    def execute(self, path: str) -> str:
        snapshot = self._world_state_gateway.build_snapshot()
        return self._persistence.write(path, snapshot)
