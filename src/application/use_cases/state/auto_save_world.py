from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class AutosaveWorldState:
    def __init__(
        self,
        world_state_gateway: WorldStateGatewayPort,
        persistence: WorldStatePersistencePort,
        default_path: str,
    ) -> None:
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence
        self._default_path = default_path

    def execute(self) -> str:
        snapshot = self._world_state_gateway.build_snapshot()
        return self._persistence.write(self._default_path, snapshot)
