from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class SaveWorldStateUseCase:
    """Persist the current runtime world state to storage.

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
        """Build a snapshot and write it to persistence.

        Args:
            path: Target filename or path for the snapshot file.

        Returns:
            The resolved absolute path written by the persistence adapter.

        Raises:
            OSError: If the persistence adapter cannot write the snapshot.
            ValueError: If the persistence adapter rejects the requested path.
        """
        snapshot = self._world_state_gateway.build_snapshot()
        return self._persistence.write(path, snapshot)
