"""Use case for saving runtime world state to persistence."""

import logging

from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import WorldStatePersistenceError
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.state.path_validation import validate_world_state_path
from src.domain.enums.auth import Permission
from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort

logger = logging.getLogger(__name__)


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
            PermissionError: If the caller lacks save-state permission.
            ValidationError: If the requested path is invalid.
            WorldStatePersistenceError: If the snapshot cannot be written.
        """
        stripped_path = validate_world_state_path(path)

        logger.info("Saving world-state snapshot to %r.", stripped_path)
        snapshot = self._world_state_gateway.build_snapshot()
        logger.debug(
            "Built world-state snapshot with %d customers, %d packages, %d routes, and %d trucks.",
            len(snapshot.world.customers),
            len(snapshot.world.packages),
            len(snapshot.world.routes),
            len(snapshot.world.trucks),
        )
        try:
            written_path = self._persistence.write(stripped_path, snapshot)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        except OSError as exc:
            raise WorldStatePersistenceError("Could not write world state snapshot.") from exc

        logger.info("World-state snapshot saved to %r.", written_path)
        return written_path
