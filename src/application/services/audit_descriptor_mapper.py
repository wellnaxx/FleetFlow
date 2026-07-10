"""Translate published events into normalized audit descriptor fields.

The mapper owns event-specific audit semantics. It converts concrete domain
and application events into stable resource/action fields plus a JSON-safe
payload. Universal event and envelope metadata is added later by the audit
event handler when it builds an ``AuditRecordDraft``.
"""

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.events.auth_events import (
    AuthorizationDenied,
    UserAuthenticated,
    UserLoginRejected,
    UserPasswordChanged,
    UserPasswordChangeRejected,
    UserPasswordReset,
    UserPasswordResetRejected,
    UserRegistered,
    UserRegistrationRejected,
    UserSessionEnded,
    UserTokensRevoked,
)
from src.application.events.startup_events import FleetSeeded
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
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.domain.events.customer_events import CustomerCreated
from src.domain.events.package_events import PackageCreated, PackageDelivered, PackagePickedUp, PackageRemoved
from src.domain.events.route_events import (
    PackageAssignedToRoute,
    PackageDetachedFromRoute,
    RouteCompleted,
    RouteCreated,
    RouteRemoved,
    RouteScheduled,
    RouteStarted,
    TruckAssignedToRoute,
    TruckReleasedFromRoute,
)
from src.shared.event import Event
from src.shared.json_types import JSONObject


def map_event_to_audit_descriptor(event: Event) -> AuditDescriptor:
    """Map one concrete event to normalized audit fields.

    Args:
        event: Domain or application event to audit.

    Returns:
        Audit descriptor containing the affected resource, normalized action,
        and event-specific JSON payload.

    Raises:
        ValueError: If the event type has no audit mapping.
    """
    match event:
        case CustomerCreated():
            return AuditDescriptor(
                resource_type=AuditResourceType.CUSTOMER,
                resource_id=str(event.customer_id),
                action=AuditAction.CREATED,
                payload_json={
                    "customer_id": str(event.customer_id),
                },
            )
        case PackageCreated():
            return AuditDescriptor(
                resource_type=AuditResourceType.PACKAGE,
                resource_id=str(event.package_id),
                action=AuditAction.CREATED,
                payload_json={
                    "package_id": str(event.package_id),
                    "customer_id": str(event.customer_id),
                    "start_location": str(event.start_location),
                    "end_location": str(event.end_location),
                    "weight": event.weight,
                    "initial_status": event.initial_status.value,
                    "initial_location": str(event.initial_location),
                    "expected_arrival": event.expected_arrival.isoformat()
                    if event.expected_arrival is not None
                    else None,
                },
            )
        case PackageRemoved():
            return AuditDescriptor(
                resource_type=AuditResourceType.PACKAGE,
                resource_id=str(event.package_id),
                action=AuditAction.REMOVED,
                payload_json={
                    "package_id": str(event.package_id),
                    "customer_id": str(event.customer_id),
                    "previous_route_id": str(event.previous_route_id)
                    if event.previous_route_id is not None
                    else None,
                    "previous_status": event.previous_status.value,
                    "previous_location": str(event.previous_location),
                    "start_location": str(event.start_location),
                    "end_location": str(event.end_location),
                    "weight": event.weight,
                    "previous_expected_arrival": event.previous_expected_arrival.isoformat()
                    if event.previous_expected_arrival is not None
                    else None,
                },
            )
        case PackagePickedUp():
            return AuditDescriptor(
                resource_type=AuditResourceType.PACKAGE,
                resource_id=str(event.package_id),
                action=AuditAction.PICKED_UP,
                payload_json={
                    "package_id": str(event.package_id),
                    "route_id": str(event.route_id),
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                    "previous_location": str(event.previous_location),
                    "new_location": str(event.new_location),
                    "scheduled_arrival": event.scheduled_arrival.isoformat()
                    if event.scheduled_arrival is not None
                    else None,
                },
            )
        case PackageDelivered():
            return AuditDescriptor(
                resource_type=AuditResourceType.PACKAGE,
                resource_id=str(event.package_id),
                action=AuditAction.DELIVERED,
                payload_json={
                    "package_id": str(event.package_id),
                    "route_id": str(event.route_id),
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                    "previous_location": str(event.previous_location),
                    "new_location": str(event.new_location),
                    "scheduled_arrival": event.scheduled_arrival.isoformat()
                    if event.scheduled_arrival is not None
                    else None,
                },
            )
        case RouteCreated():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.route_id),
                action=AuditAction.CREATED,
                payload_json={
                    "route_id": str(event.route_id),
                    "locations": [str(location) for location in event.locations],
                    "departure_time": event.departure_time.isoformat()
                    if event.departure_time is not None
                    else None,
                    "initial_status": event.initial_status.value,
                    "expected_completion_time": event.expected_completion_time.isoformat()
                    if event.expected_completion_time is not None
                    else None,
                },
            )
        case RouteScheduled():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.route_id),
                action=AuditAction.SCHEDULED,
                payload_json={
                    "route_id": str(event.route_id),
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                    "previous_departure_time": event.previous_departure_time.isoformat()
                    if event.previous_departure_time is not None
                    else None,
                    "new_departure_time": event.new_departure_time.isoformat(),
                    "previous_expected_completion_time": event.previous_expected_completion_time.isoformat()
                    if event.previous_expected_completion_time is not None
                    else None,
                    "new_expected_completion_time": event.new_expected_completion_time.isoformat(),
                },
            )
        case PackageAssignedToRoute():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.new_route_id),
                action=AuditAction.ASSIGNED_TO_ROUTE,
                payload_json={
                    "package_id": str(event.package_id),
                    "previous_route_id": _optional_id(event.previous_route_id),
                    "new_route_id": _optional_id(event.new_route_id),
                    "previous_expected_arrival": event.previous_expected_arrival.isoformat()
                    if event.previous_expected_arrival is not None
                    else None,
                    "new_expected_arrival": event.new_expected_arrival.isoformat()
                    if event.new_expected_arrival is not None
                    else None,
                },
            )
        case PackageDetachedFromRoute():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.previous_route_id),
                action=AuditAction.DETACHED_FROM_ROUTE,
                payload_json={
                    "package_id": str(event.package_id),
                    "previous_route_id": _optional_id(event.previous_route_id),
                    "new_route_id": _optional_id(event.new_route_id),
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                    "previous_location": str(event.previous_location),
                    "new_location": str(event.new_location),
                    "previous_expected_arrival": event.previous_expected_arrival.isoformat()
                    if event.previous_expected_arrival is not None
                    else None,
                    "new_expected_arrival": event.new_expected_arrival.isoformat()
                    if event.new_expected_arrival is not None
                    else None,
                    "reason": event.reason.value,
                },
            )
        case TruckAssignedToRoute():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.new_route_id),
                action=AuditAction.ASSIGNED_TO_TRUCK,
                payload_json={
                    "truck_id": str(event.truck_id),
                    "previous_route_id": _optional_id(event.previous_route_id),
                    "new_route_id": _optional_id(event.new_route_id),
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                    "previous_location": str(event.previous_location),
                    "new_location": str(event.new_location),
                    "previous_busy_from": event.previous_busy_from.isoformat()
                    if event.previous_busy_from is not None
                    else None,
                    "new_busy_from": event.new_busy_from.isoformat()
                    if event.new_busy_from is not None
                    else None,
                    "previous_busy_until": event.previous_busy_until.isoformat()
                    if event.previous_busy_until is not None
                    else None,
                    "new_busy_until": event.new_busy_until.isoformat()
                    if event.new_busy_until is not None
                    else None,
                },
            )
        case TruckReleasedFromRoute():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.previous_route_id),
                action=AuditAction.RELEASED_TRUCK,
                payload_json={
                    "truck_id": str(event.truck_id),
                    "previous_route_id": _optional_id(event.previous_route_id),
                    "new_route_id": _optional_id(event.new_route_id),
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                    "previous_location": str(event.previous_location),
                    "new_location": str(event.new_location),
                    "previous_busy_from": event.previous_busy_from.isoformat()
                    if event.previous_busy_from is not None
                    else None,
                    "new_busy_from": event.new_busy_from.isoformat()
                    if event.new_busy_from is not None
                    else None,
                    "previous_busy_until": event.previous_busy_until.isoformat()
                    if event.previous_busy_until is not None
                    else None,
                    "new_busy_until": event.new_busy_until.isoformat()
                    if event.new_busy_until is not None
                    else None,
                    "reason": event.reason.value,
                },
            )
        case RouteStarted():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.route_id),
                action=AuditAction.STARTED,
                payload_json={
                    "route_id": str(event.route_id),
                    "start_time": event.occurred_at.isoformat(),
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                },
            )
        case RouteCompleted():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.route_id),
                action=AuditAction.COMPLETED,
                payload_json={
                    "route_id": str(event.route_id),
                    "previous_status": event.previous_status.value,
                    "new_status": event.new_status.value,
                    "departure_time": event.departure_time.isoformat(),
                    "expected_completion_time": event.expected_completion_time.isoformat(),
                    "completion_time": event.occurred_at.isoformat(),
                },
            )
        case RouteRemoved():
            return AuditDescriptor(
                resource_type=AuditResourceType.ROUTE,
                resource_id=str(event.route_id),
                action=AuditAction.REMOVED,
                payload_json={
                    "route_id": str(event.route_id),
                    "previous_status": event.previous_status.value,
                    "previous_locations": [str(location) for location in event.previous_locations],
                    "previous_expected_completion_time": event.previous_expected_completion_time.isoformat()
                    if event.previous_expected_completion_time is not None
                    else None,
                    "detached_package_ids": [str(package_id) for package_id in event.detached_package_ids],
                    "released_truck_id": _optional_id(event.released_truck_id),
                },
            )
        case UserRegistered():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=str(event.user_id),
                action=AuditAction.REGISTERED,
                payload_json={
                    "user_id": str(event.user_id),
                    "username": event.username,
                    "role": event.role.value,
                },
            )
        case UserRegistrationRejected():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=None,
                action=AuditAction.REGISTRATION_REJECTED,
                payload_json={
                    "username": event.username,
                    "reason": event.reason.value,
                },
            )
        case UserPasswordChanged():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=str(event.user_id),
                action=AuditAction.PASSWORD_CHANGED,
                payload_json={
                    "user_id": str(event.user_id),
                    "username": event.username,
                },
            )
        case UserPasswordChangeRejected():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=_optional_id(event.user_id),
                action=AuditAction.PASSWORD_CHANGE_REJECTED,
                payload_json={
                    "user_id": _optional_id(event.user_id),
                    "username": event.username,
                    "reason": event.reason.value,
                },
            )
        case UserPasswordReset():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=str(event.user_id),
                action=AuditAction.PASSWORD_RESET,
                payload_json={
                    "user_id": str(event.user_id),
                    "username": event.username,
                },
            )
        case UserPasswordResetRejected():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=_optional_id(event.user_id),
                action=AuditAction.PASSWORD_RESET_REJECTED,
                payload_json={
                    "user_id": _optional_id(event.user_id),
                    "username": event.username,
                    "reason": event.reason.value,
                },
            )
        case UserAuthenticated():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=str(event.user_id),
                action=AuditAction.AUTHENTICATED,
                payload_json={
                    "user_id": str(event.user_id),
                    "username": event.username,
                    "role": event.role.value,
                },
            )
        case UserLoginRejected():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=_optional_id(event.user_id),
                action=AuditAction.LOGIN_REJECTED,
                payload_json={
                    "user_id": _optional_id(event.user_id),
                    "username": event.username,
                    "reason": event.reason.value,
                },
            )
        case UserSessionEnded():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=str(event.user_id),
                action=AuditAction.SESSION_ENDED,
                payload_json={
                    "user_id": str(event.user_id),
                    "username": event.username,
                },
            )
        case UserTokensRevoked():
            return AuditDescriptor(
                resource_type=AuditResourceType.USER,
                resource_id=str(event.user_id),
                action=AuditAction.TOKENS_REVOKED,
                payload_json={
                    "user_id": str(event.user_id),
                    "username": event.username,
                    "reason": event.reason.value,
                },
            )
        case AuthorizationDenied():
            return AuditDescriptor(
                resource_type=AuditResourceType.AUTHORIZATION,
                resource_id=_optional_id(event.user_id),
                action=AuditAction.AUTHORIZATION_DENIED,
                payload_json={
                    "user_id": _optional_id(event.user_id),
                    "username": event.username,
                    "required_permissions": [permission.name for permission in event.required_permissions],
                },
            )
        case FleetSeeded():
            return AuditDescriptor(
                resource_type=AuditResourceType.FLEET,
                resource_id=None,
                action=AuditAction.SEEDED,
                payload_json={
                    "seeded_truck_ids": list(event.seeded_truck_ids),
                    "truck_count": event.truck_count,
                    "backend": event.backend,
                },
            )
        case WorldStateExported():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.EXPORTED,
                payload_json={
                    "snapshot_path": event.snapshot_path,
                    "schema_version": event.schema_version,
                    "entity_counts": _entity_counts_payload(event.entity_counts),
                },
            )
        case WorldStateExportFailed():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.EXPORT_FAILED,
                payload_json={
                    "snapshot_path": event.snapshot_path,
                    "schema_version": event.schema_version,
                    "reason": event.reason.value,
                },
            )
        case WorldStateImported():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.IMPORTED,
                payload_json={
                    "snapshot_path": event.snapshot_path,
                    "schema_version": event.schema_version,
                    "previous_entity_counts": _entity_counts_payload(event.previous_entity_counts),
                    "new_entity_counts": _entity_counts_payload(event.new_entity_counts),
                },
            )
        case WorldStateImportFailed():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.IMPORT_FAILED,
                payload_json={
                    "snapshot_path": event.snapshot_path,
                    "schema_version": event.schema_version,
                    "reason": event.reason.value,
                },
            )
        case WorldStateCorruptionDetected():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.CORRUPTION_DETECTED,
                payload_json={
                    "snapshot_path": event.snapshot_path,
                    "reason": event.reason.value,
                },
            )
        case WorldStateSnapshotQuarantined():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.SNAPSHOT_QUARANTINED,
                payload_json={
                    "original_path": event.original_path,
                    "quarantined_path": event.quarantined_path,
                    "reason": event.reason.value,
                },
            )
        case WorldStateRuntimeSwapped():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.RUNTIME_SWAPPED,
                payload_json={
                    "snapshot_path": event.snapshot_path,
                    "schema_version": event.schema_version,
                    "previous_entity_counts": _entity_counts_payload(event.previous_entity_counts),
                    "new_entity_counts": _entity_counts_payload(event.new_entity_counts),
                },
            )
        case WorldStateStartupRestored():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.STARTUP_RESTORED,
                payload_json={
                    "snapshot_path": event.snapshot_path,
                    "schema_version": event.schema_version,
                    "previous_entity_counts": _entity_counts_payload(event.previous_entity_counts),
                    "new_entity_counts": _entity_counts_payload(event.new_entity_counts),
                },
            )
        case WorldStateStartupRestoreSkipped():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.STARTUP_RESTORE_SKIPPED,
                payload_json={
                    "reason": event.reason.value,
                },
            )
        case WorldStateStartupRestoreFailed():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.STARTUP_RESTORE_FAILED,
                payload_json={
                    "snapshot_path": event.snapshot_path,
                    "schema_version": event.schema_version,
                    "reason": event.reason.value,
                },
            )
        case WorldStateAdvanced():
            return AuditDescriptor(
                resource_type=AuditResourceType.WORLD_STATE,
                resource_id=None,
                action=AuditAction.ADVANCED,
                payload_json={
                    "routes_updated": event.routes_updated,
                    "packages_updated": event.packages_updated,
                    "trucks_moved": event.trucks_moved,
                    "trucks_released": event.trucks_released,
                },
            )
        case _:
            raise ValueError(f"Unsupported event type: {type(event).__name__}")


def _optional_id(value: object | None) -> str | None:
    """Serialize an optional event identifier for JSON payload storage."""
    return str(value) if value is not None else None


def _entity_counts_payload(entity_counts: WorldStateEntityCounts) -> JSONObject:
    """Serialize world-state entity counts into a JSON payload object."""
    return {
        "customers": entity_counts.customers,
        "packages": entity_counts.packages,
        "routes": entity_counts.routes,
        "trucks": entity_counts.trucks,
    }
