"""Use case for loading persisted world state into runtime."""

from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import WorldStatePersistenceError
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission
from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class LoadWorldStateUseCase(AuthorizedUseCase[str]):
    """Load persisted world state into the active runtime."""

    def __init__(
        self,
        world_state_gateway: WorldStateGatewayPort,
        persistence: WorldStatePersistencePort,
        authz: AuthorizationService,
    ) -> None:
        """Initialize load dependencies.

        Args:
            world_state_gateway: Runtime gateway used to apply loaded snapshots.
            persistence: Persistence adapter used to read snapshots from disk.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence

    @requires(Permission.APP_LOAD_STATE)
    def execute(self, path: str) -> str:
        """Read persisted state and replace runtime state with a reconciled snapshot.

        Args:
            path: Source filename or path containing the world-state snapshot.

        Returns:
            The resolved absolute path read by the persistence adapter.

        Raises:
            PermissionError: If the caller lacks load-state permission.
            ValidationError: If the requested path is invalid.
            WorldStateFileNotFoundError: If the file is missing.
            WorldStateCorruptionError: If the file is malformed or fails validation.
            WorldStatePersistenceError: If the snapshot cannot be read or applied.
        """
        if not path.strip():
            raise ValidationError("World state snapshot path is required.")

        try:
            abs_path, snapshot = self._persistence.read(path)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        except OSError as exc:
            raise WorldStatePersistenceError("Could not read world state snapshot.") from exc

        self._world_state_gateway.apply_snapshot(snapshot)
        return abs_path
