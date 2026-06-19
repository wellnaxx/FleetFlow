"""Validation for world-state snapshot schema compatibility."""

from collections.abc import Collection

from src.application.dto.world_state_snapshot_dto import WorldStateSnapshot
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import WorldStateCorruptionError


class SchemaSnapshotValidator:
    """Validate schema-level snapshot rules before deeper checks run."""

    def validate(self, snapshot: WorldStateSnapshot, supported_schema_versions: Collection[int]) -> None:
        """Ensure the snapshot schema is supported and internally compatible.

        Args:
            snapshot: World-state snapshot to validate.
            supported_schema_versions: Schema versions accepted by the caller.

        Raises:
            WorldStateCorruptionError: If the schema is unsupported or has a
                schema-level structural violation.
        """
        if snapshot.schema_version not in supported_schema_versions:
            raise WorldStateCorruptionError(
                f"Unsupported schema version: {snapshot.schema_version}",
                reason=WorldStateCorruptionReason.UNSUPPORTED_SCHEMA,
            )

        if snapshot.schema_version == 1 and snapshot.world.trucks:
            raise WorldStateCorruptionError(
                "Schema v1 snapshots do not support truck runtime state.",
                reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
            )
