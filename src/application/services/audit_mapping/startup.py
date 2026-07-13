"""Audit descriptor mappings for startup events."""

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.events.startup_events import FleetSeeded
from src.application.models.audit_descriptor import AuditDescriptor
from src.application.services.audit_mapping.mapper import AuditDescriptorMapping, audit_mapping


def map_fleet_seeded(event: FleetSeeded) -> AuditDescriptor:
    """Map the fleet-seeding startup result."""
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


STARTUP_AUDIT_MAPPINGS: tuple[AuditDescriptorMapping, ...] = (
    audit_mapping(FleetSeeded, map_fleet_seeded),
)
