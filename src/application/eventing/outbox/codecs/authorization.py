"""Authorization-denial outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.auth_events import AuthorizationDenied
from src.domain.enums.auth import Permission
from src.shared.json_deserialization import parse_enum_name, parse_enum_value
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_list, require_optional_str

_AUTHORIZATION_DENIED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "attempted_operation",
    "target_resource_type",
    "target_resource_id",
    "required_permissions",
])


class AuthorizationDeniedEventPayloadCodec(EventPayloadCodec[AuthorizationDenied]):
    """Encode and decode the version-2 authorization-denied payload.

    All four payload keys are required, including ``target_resource_id`` when
    its value is null. Extra keys are rejected. Operations and resource types
    use enum values; permissions use enum names, preserving order and repeats.
    Empty permission lists are accepted by the event contract.

    Encoding expects an event with correctly typed fields. Decoding validates
    payload fields and delegates universal metadata validation to the event
    constructor. Target identifiers are preserved without trimming.
    """

    @property
    def event_class(self) -> type[AuthorizationDenied]:
        """Return the concrete event class handled by this codec."""
        return AuthorizationDenied

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``authorization_denied``."""
        return "authorization_denied"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 2

    def encode(self, event: AuthorizationDenied) -> JSONObject:
        """Build a fresh JSON payload from a typed authorization denial.

        Args:
            event: Version-2 event whose specific fields should be serialized.

        Returns:
            A new dictionary with operation and resource enum values, the
            nullable target identifier, and a new list of permission names.
            Event and envelope metadata is excluded.
        """
        return {
            "attempted_operation": event.attempted_operation.value,
            "target_resource_type": event.target_resource_type.value,
            "target_resource_id": event.target_resource_id,
            "required_permissions": [permission.name for permission in event.required_permissions],
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> AuthorizationDenied:
        """Validate a version-2 payload and reconstruct its concrete event.

        Args:
            payload: JSON object containing exactly the four expected fields.
            event_id: Original event UUID, retained during reconstruction.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            An authorization-denied event with the supplied metadata and a
            tuple of permissions. The input payload is not mutated.

        Raises:
            TypeError: If a field has the wrong runtime type, a permission
                entry is not a string, or event metadata has an invalid type.
            ValueError: If fields are missing or unexpected, an enum value or
                permission name is unknown, or timestamps use the wrong time
                domain. Unknown permission errors include the entry index and
                retain the original ``KeyError`` as their cause.
        """
        require_json_object_keys(payload, _AUTHORIZATION_DENIED_PAYLOAD_KEYS)

        attempted_operation = parse_enum_value(
            payload["attempted_operation"], "attempted_operation", AuthorizationOperation
        )
        target_resource_type = parse_enum_value(
            payload["target_resource_type"], "target_resource_type", AuditResourceType
        )
        target_resource_id = require_optional_str(payload["target_resource_id"], "target_resource_id")
        raw_permissions = require_list(payload["required_permissions"], "required_permissions")

        permissions: list[Permission] = []
        for index, item in enumerate(raw_permissions):
            field_name = f"required_permissions[{index}]"
            permissions.append(parse_enum_name(item, field_name, Permission))

        return AuthorizationDenied(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            attempted_operation=attempted_operation,
            target_resource_type=target_resource_type,
            target_resource_id=target_resource_id,
            required_permissions=tuple(permissions),
        )
