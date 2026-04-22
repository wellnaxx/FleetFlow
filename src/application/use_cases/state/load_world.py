from src.application.use_cases.state.advance_world_state import AdvanceWorldStateUseCase
from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class LoadWorldStateUseCase:
    """Load persisted world state into the active runtime.

    Authorization is intentionally enforced by the driving adapter command
    boundary, not inside this use case. Any caller outside that boundary is
    responsible for applying authorization before invoking it.
    """

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
        """Read persisted state, replace runtime state, and refresh derived data.

        Args:
            path: Source filename or path containing the world-state snapshot.

        Returns:
            The resolved absolute path read by the persistence adapter.

        Raises:
            OSError: If the persistence adapter cannot read the snapshot.
            ValueError: If the file is missing, malformed, or fails validation.
        """
        abs_path, snapshot = self._persistence.read(path)
        self._world_state_gateway.apply_snapshot(snapshot)
        self._advance_world_state.execute()
        return abs_path
