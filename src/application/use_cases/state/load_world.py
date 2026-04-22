from src.application.use_cases.state.advance_world_state import AdvanceWorldStateUseCase
from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class LoadWorldStateUseCase:
    def __init__(
        self,
        world_state_gateway: WorldStateGatewayPort,
        persistence: WorldStatePersistencePort,
        advance_world_state: AdvanceWorldStateUseCase,
    ) -> None:
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence
        self._advance_world_state = advance_world_state

    def execute(self, path: str) -> str:
        abs_path, snapshot = self._persistence.read(path)
        self._world_state_gateway.apply_snapshot(snapshot)
        self._advance_world_state.execute()
        return abs_path
