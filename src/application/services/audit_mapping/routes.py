"""Audit descriptor mappings for route aggregate events."""

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.models.audit_descriptor import AuditDescriptor
from src.application.services.audit_mapping.mapper import AuditDescriptorMapping, audit_mapping
from src.application.services.audit_mapping.serialization import optional_id
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


def map_route_created(event: RouteCreated) -> AuditDescriptor:
    """Map route creation and its initial schedule state."""
    return AuditDescriptor(
        resource_type=AuditResourceType.ROUTE,
        resource_id=str(event.route_id),
        action=AuditAction.CREATED,
        payload_json={
            "route_id": str(event.route_id),
            "locations": [str(location) for location in event.locations],
            "departure_time": (
                event.departure_time.isoformat() if event.departure_time is not None else None
            ),
            "initial_status": event.initial_status.value,
            "expected_completion_time": (
                event.expected_completion_time.isoformat()
                if event.expected_completion_time is not None
                else None
            ),
        },
    )


def map_route_scheduled(event: RouteScheduled) -> AuditDescriptor:
    """Map route schedule replacement and status transition."""
    return AuditDescriptor(
        resource_type=AuditResourceType.ROUTE,
        resource_id=str(event.route_id),
        action=AuditAction.SCHEDULED,
        payload_json={
            "route_id": str(event.route_id),
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_departure_time": (
                event.previous_departure_time.isoformat()
                if event.previous_departure_time is not None
                else None
            ),
            "new_departure_time": event.new_departure_time.isoformat(),
            "previous_expected_completion_time": (
                event.previous_expected_completion_time.isoformat()
                if event.previous_expected_completion_time is not None
                else None
            ),
            "new_expected_completion_time": event.new_expected_completion_time.isoformat(),
        },
    )


def map_package_assigned_to_route(event: PackageAssignedToRoute) -> AuditDescriptor:
    """Map package attachment to a route."""
    return AuditDescriptor(
        resource_type=AuditResourceType.ROUTE,
        resource_id=str(event.new_route_id),
        action=AuditAction.ASSIGNED_TO_ROUTE,
        payload_json={
            "package_id": str(event.package_id),
            "previous_route_id": optional_id(event.previous_route_id),
            "new_route_id": optional_id(event.new_route_id),
            "previous_expected_arrival": (
                event.previous_expected_arrival.isoformat()
                if event.previous_expected_arrival is not None
                else None
            ),
            "new_expected_arrival": (
                event.new_expected_arrival.isoformat()
                if event.new_expected_arrival is not None
                else None
            ),
        },
    )


def map_package_detached_from_route(event: PackageDetachedFromRoute) -> AuditDescriptor:
    """Map package detachment and its resulting package state."""
    return AuditDescriptor(
        resource_type=AuditResourceType.ROUTE,
        resource_id=str(event.previous_route_id),
        action=AuditAction.DETACHED_FROM_ROUTE,
        payload_json={
            "package_id": str(event.package_id),
            "previous_route_id": optional_id(event.previous_route_id),
            "new_route_id": optional_id(event.new_route_id),
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_location": str(event.previous_location),
            "new_location": str(event.new_location),
            "previous_expected_arrival": (
                event.previous_expected_arrival.isoformat()
                if event.previous_expected_arrival is not None
                else None
            ),
            "new_expected_arrival": (
                event.new_expected_arrival.isoformat()
                if event.new_expected_arrival is not None
                else None
            ),
            "reason": event.reason.value,
        },
    )


def map_truck_assigned_to_route(event: TruckAssignedToRoute) -> AuditDescriptor:
    """Map truck attachment and its resulting operational state."""
    return AuditDescriptor(
        resource_type=AuditResourceType.ROUTE,
        resource_id=str(event.new_route_id),
        action=AuditAction.ASSIGNED_TO_TRUCK,
        payload_json={
            "truck_id": str(event.truck_id),
            "previous_route_id": optional_id(event.previous_route_id),
            "new_route_id": optional_id(event.new_route_id),
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_location": str(event.previous_location),
            "new_location": str(event.new_location),
            "previous_busy_from": (
                event.previous_busy_from.isoformat() if event.previous_busy_from is not None else None
            ),
            "new_busy_from": (
                event.new_busy_from.isoformat() if event.new_busy_from is not None else None
            ),
            "previous_busy_until": (
                event.previous_busy_until.isoformat()
                if event.previous_busy_until is not None
                else None
            ),
            "new_busy_until": (
                event.new_busy_until.isoformat() if event.new_busy_until is not None else None
            ),
        },
    )


def map_truck_released_from_route(event: TruckReleasedFromRoute) -> AuditDescriptor:
    """Map truck detachment and its resulting operational state."""
    return AuditDescriptor(
        resource_type=AuditResourceType.ROUTE,
        resource_id=str(event.previous_route_id),
        action=AuditAction.RELEASED_TRUCK,
        payload_json={
            "truck_id": str(event.truck_id),
            "previous_route_id": optional_id(event.previous_route_id),
            "new_route_id": optional_id(event.new_route_id),
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_location": str(event.previous_location),
            "new_location": str(event.new_location),
            "previous_busy_from": (
                event.previous_busy_from.isoformat() if event.previous_busy_from is not None else None
            ),
            "new_busy_from": (
                event.new_busy_from.isoformat() if event.new_busy_from is not None else None
            ),
            "previous_busy_until": (
                event.previous_busy_until.isoformat()
                if event.previous_busy_until is not None
                else None
            ),
            "new_busy_until": (
                event.new_busy_until.isoformat() if event.new_busy_until is not None else None
            ),
            "reason": event.reason.value,
        },
    )


def map_route_started(event: RouteStarted) -> AuditDescriptor:
    """Map route start and status transition."""
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


def map_route_completed(event: RouteCompleted) -> AuditDescriptor:
    """Map route completion and schedule outcome."""
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


def map_route_removed(event: RouteRemoved) -> AuditDescriptor:
    """Map route removal and detached aggregate references."""
    return AuditDescriptor(
        resource_type=AuditResourceType.ROUTE,
        resource_id=str(event.route_id),
        action=AuditAction.REMOVED,
        payload_json={
            "route_id": str(event.route_id),
            "previous_status": event.previous_status.value,
            "previous_locations": [str(location) for location in event.previous_locations],
            "previous_expected_completion_time": (
                event.previous_expected_completion_time.isoformat()
                if event.previous_expected_completion_time is not None
                else None
            ),
            "detached_package_ids": [str(package_id) for package_id in event.detached_package_ids],
            "released_truck_id": optional_id(event.released_truck_id),
        },
    )


ROUTE_AUDIT_MAPPINGS: tuple[AuditDescriptorMapping, ...] = (
    audit_mapping(RouteCreated, map_route_created),
    audit_mapping(RouteScheduled, map_route_scheduled),
    audit_mapping(PackageAssignedToRoute, map_package_assigned_to_route),
    audit_mapping(PackageDetachedFromRoute, map_package_detached_from_route),
    audit_mapping(TruckAssignedToRoute, map_truck_assigned_to_route),
    audit_mapping(TruckReleasedFromRoute, map_truck_released_from_route),
    audit_mapping(RouteStarted, map_route_started),
    audit_mapping(RouteCompleted, map_route_completed),
    audit_mapping(RouteRemoved, map_route_removed),
)
