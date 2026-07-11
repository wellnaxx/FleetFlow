"""Application events describing world-state persistence workflows."""

from dataclasses import dataclass
from typing import ClassVar

from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.enums.world_state_startup_skip_reasons import WorldStateStartupSkipReason
from src.application.events.base import ApplicationEvent
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateExported(ApplicationEvent):
    """Event recorded when the world state is exported to a file."""

    snapshot_path: str
    schema_version: int
    entity_counts: WorldStateEntityCounts


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateExportFailed(ApplicationEvent):
    """Event recorded when a world state export operation fails."""

    snapshot_path: str
    schema_version: int | None
    reason: WorldStateFailureReason


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateImported(ApplicationEvent):
    """Event recorded when the world state is imported from a file."""
    event_version: ClassVar[int] = 2

    snapshot_path: str
    schema_version: int
    previous_entity_counts: WorldStateEntityCounts
    new_entity_counts: WorldStateEntityCounts


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateImportFailed(ApplicationEvent):
    """Event recorded when a world state import operation fails."""

    snapshot_path: str
    schema_version: int | None
    reason: WorldStateFailureReason


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateCorruptionDetected(ApplicationEvent):
    """Event recorded when corruption is detected in the world state."""

    snapshot_path: str
    reason: WorldStateCorruptionReason


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateSnapshotQuarantined(ApplicationEvent):
    """Event recorded when a corrupt snapshot is moved to quarantine."""

    original_path: str
    quarantined_path: str
    reason: WorldStateCorruptionReason


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateRuntimeSwapped(ApplicationEvent):
    """Event recorded when the in-memory runtime state is atomically replaced."""
    event_version: ClassVar[int] = 2

    snapshot_path: str
    schema_version: int
    previous_entity_counts: WorldStateEntityCounts
    new_entity_counts: WorldStateEntityCounts


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateStartupRestored(ApplicationEvent):
    """Event recorded when world state is automatically restored at startup."""
    event_version: ClassVar[int] = 2

    snapshot_path: str
    schema_version: int
    previous_entity_counts: WorldStateEntityCounts
    new_entity_counts: WorldStateEntityCounts


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateStartupRestoreSkipped(ApplicationEvent):
    """Event recorded when startup world state restore is skipped."""

    reason: WorldStateStartupSkipReason


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateStartupRestoreFailed(ApplicationEvent):
    """Event recorded when startup world state restore fails."""

    snapshot_path: str
    schema_version: int | None
    reason: WorldStateFailureReason


@dataclass(frozen=True, slots=True, kw_only=True)
class WorldStateAdvanced(ApplicationEvent):
    """Event recorded when the heartbeat advances world state.

    Attributes:
        routes_updated: Number of routes whose runtime state changed.
        packages_updated: Number of packages whose runtime state changed.
        trucks_moved: Number of trucks whose schedule-derived position changed.
        trucks_released: Number of trucks released from completed routes.
        trucks_reconciled: Number of truck route references directly repaired.
    """

    event_version: ClassVar[int] = 2

    routes_updated: int
    packages_updated: int
    trucks_moved: int
    trucks_released: int
    trucks_reconciled: int
