"""Use case for saving runtime world state to persistence."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission
from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class SaveWorldStateUseCase(AuthorizedUseCase[str]):
    """Persist the current runtime world state to storage."""

    def __init__(
        self,
        world_state_gateway: WorldStateGatewayPort,
        persistence: WorldStatePersistencePort,
        authz: AuthorizationService,
    ) -> None:
        """Initialize save dependencies.

        Args:
            world_state_gateway: Runtime gateway used to build snapshots.
            persistence: Persistence adapter used to write snapshots to disk.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence

    @requires(Permission.APP_SAVE_STATE)
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
