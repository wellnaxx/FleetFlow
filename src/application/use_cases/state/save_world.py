"""Use case for saving runtime world state to persistence."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.events.world_state_events import WorldStateExported, WorldStateExportFailed
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import WorldStatePersistenceError
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.state.path_validation import validate_world_state_path
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.domain.enums.auth import Permission

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.ports.output.world_state_gateway import WorldStateGatewayPort
    from src.ports.output.world_state_persistence import WorldStatePersistencePort

logger = logging.getLogger(__name__)


def _resolve_path_target_id(_self: SaveWorldStateUseCase, path: str) -> str | None:
    """Resolve the audit target resource id for a world state export attempt."""
    return path.strip() or None


class SaveWorldStateUseCase(AuthorizedUseCase[str]):
    """Persist the current runtime world state to storage."""

    def __init__(
        self,
        world_state_gateway: WorldStateGatewayPort,
        persistence: WorldStatePersistencePort,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize save dependencies.

        Args:
            world_state_gateway: Runtime gateway used to build snapshots.
            persistence: Persistence adapter used to write snapshots to disk.
            authz: Service used for authorization checks.
            clock: Clock provider used to timestamp application events.
        """
        super().__init__(authz)
        self._world_state_gateway = world_state_gateway
        self._persistence = persistence

        self._clock = clock

    @requires(
        Permission.APP_SAVE_STATE,
        operation=AuthorizationOperation.WORLD_STATE_EXPORT,
        target_resource_type=AuditResourceType.WORLD_STATE,
        target_resource_id_resolver=_resolve_path_target_id,
    )
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
        occurred_at = self._clock()

        try:
            stripped_path = validate_world_state_path(path)
        except ValidationError:
            self._record_event(
                WorldStateExportFailed(
                    snapshot_path=path,
                    schema_version=None,
                    reason=WorldStateFailureReason.INVALID_PATH,
                    occurred_at=occurred_at,
                )
            )
            raise

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
            self._record_event(
                WorldStateExportFailed(
                    snapshot_path=stripped_path,
                    schema_version=snapshot.schema_version,
                    reason=WorldStateFailureReason.INVALID_PATH,
                    occurred_at=occurred_at,
                )
            )
            raise ValidationError(str(exc)) from exc
        except OSError as exc:
            self._record_event(
                WorldStateExportFailed(
                    snapshot_path=stripped_path,
                    schema_version=snapshot.schema_version,
                    reason=WorldStateFailureReason.PERSISTENCE_FAILURE,
                    occurred_at=occurred_at,
                )
            )
            raise WorldStatePersistenceError("Could not write world state snapshot.") from exc

        self._record_event(
            WorldStateExported(
                snapshot_path=written_path,
                schema_version=snapshot.schema_version,
                entity_counts=WorldStateEntityCounts(
                    customers=len(snapshot.world.customers),
                    packages=len(snapshot.world.packages),
                    routes=len(snapshot.world.routes),
                    trucks=len(snapshot.world.trucks),
                ),
                occurred_at=occurred_at,
            )
        )

        logger.info("World-state snapshot saved to %r.", written_path)
        return written_path
