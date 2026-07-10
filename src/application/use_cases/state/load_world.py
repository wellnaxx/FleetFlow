"""Use case for loading persisted world state into runtime."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.events.world_state_events import (
    WorldStateCorruptionDetected,
    WorldStateImported,
    WorldStateImportFailed,
)
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStatePersistenceError,
    WorldStateRuntimeSwapError,
)
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.application.use_cases.state.path_validation import validate_world_state_path
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.domain.enums.auth import Permission
from src.ports.output.world_state_gateway import WorldStateGatewayPort
from src.ports.output.world_state_persistence import WorldStatePersistencePort

logger = logging.getLogger(__name__)


class LoadWorldStateUseCase(AuthorizedUseCase[str], ApplicationEventRecorderMixin):
    """Load persisted world state into the active runtime."""

    def __init__(
        self,
        world_state_gateway: WorldStateGatewayPort,
        persistence: WorldStatePersistencePort,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize load dependencies.

        Args:
            world_state_gateway: Runtime gateway used to apply loaded snapshots.
            persistence: Persistence adapter used to read snapshots from disk.
            authz: Service used for authorization checks.
            clock: Clock provider used to timestamp application events.
        """
        super().__init__(authz)
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence

        self._clock = clock

        self._pending_events = []

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
            DatabaseError: If snapshot import persistence fails.
            WorldStateFileNotFoundError: If the file is missing.
            WorldStateCorruptionError: If the file is malformed or fails validation.
            WorldStatePersistenceError: If the snapshot cannot be read or applied.
        """
        occurred_at = self._clock()
        try:
            stripped_path = validate_world_state_path(path)
        except ValidationError:
            self._record_import_failed(path, None, WorldStateFailureReason.INVALID_PATH, occurred_at)
            raise

        logger.info("Loading world-state snapshot from %r.", stripped_path)
        try:
            abs_path, snapshot = self._persistence.read(stripped_path)
        except ValueError as exc:
            self._record_import_failed(stripped_path, None, WorldStateFailureReason.INVALID_PATH, occurred_at)
            raise ValidationError(str(exc)) from exc
        except OSError as exc:
            self._record_import_failed(
                stripped_path, None, WorldStateFailureReason.PERSISTENCE_FAILURE, occurred_at
            )
            raise WorldStatePersistenceError("Could not read world state snapshot.") from exc
        except WorldStateFileNotFoundError:
            self._record_import_failed(stripped_path, None, WorldStateFailureReason.FILE_NOT_FOUND, occurred_at)
            raise
        except WorldStateCorruptionError as exc:
            self._record_import_failed(
                stripped_path, None, WorldStateFailureReason.CORRUPT_SNAPSHOT, occurred_at
            )
            self._record_corruption_event(stripped_path, exc.reason, occurred_at)
            raise
        except WorldStatePersistenceError:
            self._record_import_failed(
                stripped_path, None, WorldStateFailureReason.PERSISTENCE_FAILURE, occurred_at
            )
            raise

        logger.debug(
            "Read new world-state snapshot with %d customers, %d packages, %d routes, and %d trucks.",
            len(snapshot.world.customers),
            len(snapshot.world.packages),
            len(snapshot.world.routes),
            len(snapshot.world.trucks),
        )

        previous_snapshot = self._world_state_gateway.build_snapshot()
        logger.debug(
            "Read current world-state runtime with %d customers, %d packages, %d routes, and %d trucks.",
            len(previous_snapshot.world.customers),
            len(previous_snapshot.world.packages),
            len(previous_snapshot.world.routes),
            len(previous_snapshot.world.trucks),
        )

        try:
            self._world_state_gateway.apply_snapshot(snapshot)
        except WorldStateCorruptionError as exc:
            self._record_import_failed(
                abs_path, snapshot.schema_version, WorldStateFailureReason.CORRUPT_SNAPSHOT, occurred_at
            )
            self._record_corruption_event(abs_path, exc.reason, occurred_at)
            raise
        except WorldStateRuntimeSwapError:
            self._record_import_failed(
                abs_path, snapshot.schema_version, WorldStateFailureReason.RUNTIME_SWAP_FAILURE, occurred_at
            )
            raise
        except DatabaseError:
            self._record_import_failed(
                abs_path, snapshot.schema_version, WorldStateFailureReason.PERSISTENCE_FAILURE, occurred_at
            )
            raise

        self._record_event(
            WorldStateImported(
                snapshot_path=abs_path,
                schema_version=snapshot.schema_version,
                previous_entity_counts=WorldStateEntityCounts(
                    customers=len(previous_snapshot.world.customers),
                    packages=len(previous_snapshot.world.packages),
                    routes=len(previous_snapshot.world.routes),
                    trucks=len(previous_snapshot.world.trucks),
                ),
                new_entity_counts=WorldStateEntityCounts(
                    customers=len(snapshot.world.customers),
                    packages=len(snapshot.world.packages),
                    routes=len(snapshot.world.routes),
                    trucks=len(snapshot.world.trucks),
                ),
                occurred_at=occurred_at,
            )
        )

        logger.info("World-state snapshot loaded from %r.", abs_path)
        return abs_path

    def _record_import_failed(
        self,
        snapshot_path: str,
        schema_version: int | None,
        reason: WorldStateFailureReason,
        occurred_at: datetime,
    ) -> None:
        self._record_event(
            WorldStateImportFailed(
                snapshot_path=snapshot_path,
                schema_version=schema_version,
                reason=reason,
                occurred_at=occurred_at,
            )
        )

    def _record_corruption_event(
        self,
        snapshot_path: str,
        reason: WorldStateCorruptionReason,
        occurred_at: datetime,
    ) -> None:
        self._record_event(
            WorldStateCorruptionDetected(
                snapshot_path=snapshot_path,
                reason=reason,
                occurred_at=occurred_at,
            )
        )
