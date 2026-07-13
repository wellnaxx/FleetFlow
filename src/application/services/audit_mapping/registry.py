"""Assemble the complete set of explicit audit descriptor mappings."""

from src.application.services.audit_mapping.auth import AUTH_AUDIT_MAPPINGS
from src.application.services.audit_mapping.customers import CUSTOMER_AUDIT_MAPPINGS
from src.application.services.audit_mapping.mapper import AuditDescriptorMapper, AuditDescriptorMapping
from src.application.services.audit_mapping.packages import PACKAGE_AUDIT_MAPPINGS
from src.application.services.audit_mapping.reconciliation import RECONCILIATION_AUDIT_MAPPINGS
from src.application.services.audit_mapping.routes import ROUTE_AUDIT_MAPPINGS
from src.application.services.audit_mapping.startup import STARTUP_AUDIT_MAPPINGS
from src.application.services.audit_mapping.world_state import WORLD_STATE_AUDIT_MAPPINGS

AUDIT_MAPPINGS: tuple[AuditDescriptorMapping, ...] = (
    *CUSTOMER_AUDIT_MAPPINGS,
    *PACKAGE_AUDIT_MAPPINGS,
    *ROUTE_AUDIT_MAPPINGS,
    *AUTH_AUDIT_MAPPINGS,
    *STARTUP_AUDIT_MAPPINGS,
    *WORLD_STATE_AUDIT_MAPPINGS,
    *RECONCILIATION_AUDIT_MAPPINGS,
)


def build_audit_descriptor_mapper() -> AuditDescriptorMapper:
    """Build the application mapper from all explicit event registrations."""
    return AuditDescriptorMapper(AUDIT_MAPPINGS)
