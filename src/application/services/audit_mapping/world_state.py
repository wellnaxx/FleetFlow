"""Audit descriptor mappings for world-state workflow events."""

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.events.world_state_events import (
    WorldStateAdvanced,
    WorldStateCorruptionDetected,
    WorldStateExported,
    WorldStateExportFailed,
    WorldStateImported,
    WorldStateImportFailed,
    WorldStateRuntimeSwapped,
    WorldStateSnapshotQuarantined,
    WorldStateStartupRestored,
    WorldStateStartupRestoreFailed,
    WorldStateStartupRestoreSkipped,
)
from src.application.models.audit_descriptor import AuditDescriptor
from src.application.services.audit_mapping.mapper import AuditDescriptorMapping, audit_mapping
from src.application.services.audit_mapping.serialization import entity_counts_payload
from src.shared.json_types import JSONObject


def map_world_state_exported(event: WorldStateExported) -> AuditDescriptor:
    """Map successful world-state export."""
    return _world_state_descriptor(
        AuditAction.EXPORTED,
        {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "entity_counts": entity_counts_payload(event.entity_counts),
        },
    )


def map_world_state_export_failed(event: WorldStateExportFailed) -> AuditDescriptor:
    """Map failed world-state export."""
    return _world_state_descriptor(
        AuditAction.EXPORT_FAILED,
        {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "reason": event.reason.value,
        },
    )


def map_world_state_imported(event: WorldStateImported) -> AuditDescriptor:
    """Map successful world-state import."""
    return _world_state_descriptor(
        AuditAction.IMPORTED,
        {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "previous_entity_counts": entity_counts_payload(event.previous_entity_counts),
            "new_entity_counts": entity_counts_payload(event.new_entity_counts),
        },
    )


def map_world_state_import_failed(event: WorldStateImportFailed) -> AuditDescriptor:
    """Map failed world-state import."""
    return _world_state_descriptor(
        AuditAction.IMPORT_FAILED,
        {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "reason": event.reason.value,
        },
    )


def map_world_state_corruption_detected(event: WorldStateCorruptionDetected) -> AuditDescriptor:
    """Map corrupt snapshot detection."""
    return _world_state_descriptor(
        AuditAction.CORRUPTION_DETECTED,
        {"snapshot_path": event.snapshot_path, "reason": event.reason.value},
    )


def map_world_state_snapshot_quarantined(event: WorldStateSnapshotQuarantined) -> AuditDescriptor:
    """Map corrupt snapshot quarantine."""
    return _world_state_descriptor(
        AuditAction.SNAPSHOT_QUARANTINED,
        {
            "original_path": event.original_path,
            "quarantined_path": event.quarantined_path,
            "reason": event.reason.value,
        },
    )


def map_world_state_runtime_swapped(event: WorldStateRuntimeSwapped) -> AuditDescriptor:
    """Map runtime replacement after state loading."""
    return _world_state_descriptor(
        AuditAction.RUNTIME_SWAPPED,
        {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "previous_entity_counts": entity_counts_payload(event.previous_entity_counts),
            "new_entity_counts": entity_counts_payload(event.new_entity_counts),
        },
    )


def map_world_state_startup_restored(event: WorldStateStartupRestored) -> AuditDescriptor:
    """Map successful startup restoration."""
    return _world_state_descriptor(
        AuditAction.STARTUP_RESTORED,
        {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "previous_entity_counts": entity_counts_payload(event.previous_entity_counts),
            "new_entity_counts": entity_counts_payload(event.new_entity_counts),
        },
    )


def map_world_state_startup_restore_skipped(
    event: WorldStateStartupRestoreSkipped,
) -> AuditDescriptor:
    """Map intentionally skipped startup restoration."""
    return _world_state_descriptor(
        AuditAction.STARTUP_RESTORE_SKIPPED,
        {"reason": event.reason.value},
    )


def map_world_state_startup_restore_failed(event: WorldStateStartupRestoreFailed) -> AuditDescriptor:
    """Map failed startup restoration."""
    return _world_state_descriptor(
        AuditAction.STARTUP_RESTORE_FAILED,
        {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "reason": event.reason.value,
        },
    )


def map_world_state_advanced(event: WorldStateAdvanced) -> AuditDescriptor:
    """Map aggregate heartbeat advancement counts."""
    return _world_state_descriptor(
        AuditAction.ADVANCED,
        {
            "routes_updated": event.routes_updated,
            "packages_updated": event.packages_updated,
            "trucks_moved": event.trucks_moved,
            "trucks_released": event.trucks_released,
            "trucks_reconciled": event.trucks_reconciled,
        },
    )


def _world_state_descriptor(action: AuditAction, payload_json: JSONObject) -> AuditDescriptor:
    """Build a descriptor for a workflow affecting the global world state."""
    return AuditDescriptor(
        resource_type=AuditResourceType.WORLD_STATE,
        resource_id=None,
        action=action,
        payload_json=payload_json,
    )


WORLD_STATE_AUDIT_MAPPINGS: tuple[AuditDescriptorMapping, ...] = (
    audit_mapping(WorldStateExported, map_world_state_exported),
    audit_mapping(WorldStateExportFailed, map_world_state_export_failed),
    audit_mapping(WorldStateImported, map_world_state_imported),
    audit_mapping(WorldStateImportFailed, map_world_state_import_failed),
    audit_mapping(WorldStateCorruptionDetected, map_world_state_corruption_detected),
    audit_mapping(WorldStateSnapshotQuarantined, map_world_state_snapshot_quarantined),
    audit_mapping(WorldStateRuntimeSwapped, map_world_state_runtime_swapped),
    audit_mapping(WorldStateStartupRestored, map_world_state_startup_restored),
    audit_mapping(WorldStateStartupRestoreSkipped, map_world_state_startup_restore_skipped),
    audit_mapping(WorldStateStartupRestoreFailed, map_world_state_startup_restore_failed),
    audit_mapping(WorldStateAdvanced, map_world_state_advanced),
)
