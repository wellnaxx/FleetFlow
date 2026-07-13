"""Audit descriptor mappings for customer events."""

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.models.audit_descriptor import AuditDescriptor
from src.application.services.audit_mapping.mapper import AuditDescriptorMapping, audit_mapping
from src.domain.events.customer_events import CustomerCreated


def map_customer_created(event: CustomerCreated) -> AuditDescriptor:
    """Map customer creation without including contact PII."""
    return AuditDescriptor(
        resource_type=AuditResourceType.CUSTOMER,
        resource_id=str(event.customer_id),
        action=AuditAction.CREATED,
        payload_json={"customer_id": str(event.customer_id)},
    )


CUSTOMER_AUDIT_MAPPINGS: tuple[AuditDescriptorMapping, ...] = (
    audit_mapping(CustomerCreated, map_customer_created),
)
