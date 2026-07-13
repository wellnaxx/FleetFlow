"""Audit descriptor mappings for package lifecycle events."""

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.models.audit_descriptor import AuditDescriptor
from src.application.services.audit_mapping.mapper import AuditDescriptorMapping, audit_mapping
from src.application.services.audit_mapping.serialization import optional_id
from src.domain.events.package_events import PackageCreated, PackageDelivered, PackagePickedUp, PackageRemoved


def map_package_created(event: PackageCreated) -> AuditDescriptor:
    """Map package creation and its initial delivery state."""
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
            "expected_arrival": (
                event.expected_arrival.isoformat() if event.expected_arrival is not None else None
            ),
        },
    )


def map_package_removed(event: PackageRemoved) -> AuditDescriptor:
    """Map package removal and the state discarded with it."""
    return AuditDescriptor(
        resource_type=AuditResourceType.PACKAGE,
        resource_id=str(event.package_id),
        action=AuditAction.REMOVED,
        payload_json={
            "package_id": str(event.package_id),
            "customer_id": str(event.customer_id),
            "previous_route_id": optional_id(event.previous_route_id),
            "previous_status": event.previous_status.value,
            "previous_location": str(event.previous_location),
            "start_location": str(event.start_location),
            "end_location": str(event.end_location),
            "weight": event.weight,
            "previous_expected_arrival": (
                event.previous_expected_arrival.isoformat()
                if event.previous_expected_arrival is not None
                else None
            ),
        },
    )


def map_package_picked_up(event: PackagePickedUp) -> AuditDescriptor:
    """Map a package pickup state transition."""
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
            "scheduled_arrival": (
                event.scheduled_arrival.isoformat() if event.scheduled_arrival is not None else None
            ),
        },
    )


def map_package_delivered(event: PackageDelivered) -> AuditDescriptor:
    """Map a package delivery state transition."""
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
            "scheduled_arrival": (
                event.scheduled_arrival.isoformat() if event.scheduled_arrival is not None else None
            ),
        },
    )


PACKAGE_AUDIT_MAPPINGS: tuple[AuditDescriptorMapping, ...] = (
    audit_mapping(PackageCreated, map_package_created),
    audit_mapping(PackageRemoved, map_package_removed),
    audit_mapping(PackagePickedUp, map_package_picked_up),
    audit_mapping(PackageDelivered, map_package_delivered),
)
