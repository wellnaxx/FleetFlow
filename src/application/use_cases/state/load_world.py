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
    ) -> None:
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence

    def execute(self, path: str) -> str:
        """Read persisted state and replace runtime state with a reconciled snapshot.

        Args:
            path: Source filename or path containing the world-state snapshot.

        Returns:
            The resolved absolute path read by the persistence adapter.

        Raises:
            WorldStateFileNotFoundError: If the file is missing.
            WorldStateCorruptionError: If the file is malformed or fails validation.
            WorldStatePersistenceError: If the persistence adapter cannot read the snapshot.
        """
        abs_path, snapshot = self._persistence.read(path)
        self._world_state_gateway.apply_snapshot(snapshot)
        return abs_path
