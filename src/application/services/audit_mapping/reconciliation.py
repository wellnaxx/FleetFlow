"""Audit descriptor mappings for heartbeat reconciliation events."""

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.events.reconciliation_events import (
    PackageStateReconciled,
    RouteStateReconciled,
    TruckPositionReconciled,
    TruckRouteReferenceReconciled,
)
from src.application.models.audit_descriptor import AuditDescriptor
from src.application.services.audit_mapping.mapper import AuditDescriptorMapping, audit_mapping
from src.shared.json_serialization import optional_id, optional_isoformat, optional_str


def map_route_state_reconciled(event: RouteStateReconciled) -> AuditDescriptor:
    """Map a route-state correction."""
    return AuditDescriptor(
        resource_type=AuditResourceType.ROUTE,
        resource_id=str(event.route_id),
        action=AuditAction.RECONCILED,
        payload_json={
            "route_id": str(event.route_id),
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "departure_time": optional_isoformat(event.departure_time),
            "expected_completion_time": optional_isoformat(event.expected_completion_time),
            "reason": event.reason.value,
        },
    )


def map_package_state_reconciled(event: PackageStateReconciled) -> AuditDescriptor:
    """Map one package reconciliation and all reasons for its correction."""
    return AuditDescriptor(
        resource_type=AuditResourceType.PACKAGE,
        resource_id=str(event.package_id),
        action=AuditAction.RECONCILED,
        payload_json={
            "package_id": str(event.package_id),
            "route_id": optional_id(event.route_id),
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_location": str(event.previous_location),
            "new_location": str(event.new_location),
            "previous_expected_arrival": optional_isoformat(event.previous_expected_arrival),
            "new_expected_arrival": optional_isoformat(event.new_expected_arrival),
            "scheduled_pickup_time": optional_isoformat(event.scheduled_pickup_time),
            "scheduled_delivery_time": optional_isoformat(event.scheduled_delivery_time),
            "reasons": [reason.value for reason in event.reasons],
        },
    )


def map_truck_position_reconciled(event: TruckPositionReconciled) -> AuditDescriptor:
    """Map a truck-position correction."""
    return AuditDescriptor(
        resource_type=AuditResourceType.TRUCK,
        resource_id=str(event.truck_id),
        action=AuditAction.RECONCILED,
        payload_json={
            "truck_id": str(event.truck_id),
            "route_id": optional_id(event.route_id),
            "previous_location": optional_str(event.previous_location),
            "new_location": optional_str(event.new_location),
            "previous_in_transit_to": optional_str(event.previous_in_transit_to),
            "new_in_transit_to": optional_str(event.new_in_transit_to),
            "position_kind": event.position_kind.value,
        },
    )


def map_truck_route_reference_reconciled(
    event: TruckRouteReferenceReconciled,
) -> AuditDescriptor:
    """Map a repaired truck-to-route reference."""
    return AuditDescriptor(
        resource_type=AuditResourceType.TRUCK,
        resource_id=str(event.truck_id),
        action=AuditAction.RECONCILED,
        payload_json={
            "truck_id": str(event.truck_id),
            "previous_route_id": optional_id(event.previous_route_id),
            "new_route_id": str(event.new_route_id),
        },
    )


RECONCILIATION_AUDIT_MAPPINGS: tuple[AuditDescriptorMapping, ...] = (
    audit_mapping(RouteStateReconciled, map_route_state_reconciled),
    audit_mapping(PackageStateReconciled, map_package_state_reconciled),
    audit_mapping(TruckPositionReconciled, map_truck_position_reconciled),
    audit_mapping(TruckRouteReferenceReconciled, map_truck_route_reference_reconciled),
)
