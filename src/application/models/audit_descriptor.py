"""Normalized audit fields derived from one concrete event."""

from dataclasses import dataclass

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.models.audit_validation import require_enum, require_json_object, require_str
from src.shared.json_types import JSONObject


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditDescriptor:
    """Event-specific audit metadata after descriptor mapping.

    Universal event/envelope metadata stays outside this model. This object
    only describes what resource was affected, what action happened, and what
    event-specific JSON payload should be stored.
    """

    resource_type: AuditResourceType
    resource_id: str | None
    action: AuditAction
    payload_json: JSONObject

    def __post_init__(self) -> None:
        """Validate and normalize audit descriptor fields."""
        require_enum(self.resource_type, "resource_type", AuditResourceType)

        if self.resource_id is not None:
            object.__setattr__(self, "resource_id", require_str(self.resource_id, "resource_id"))

        require_enum(self.action, "action", AuditAction)
        object.__setattr__(self, "payload_json", require_json_object(self.payload_json, "payload_json"))
