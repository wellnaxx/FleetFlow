"""Concrete outbox payload codecs for authentication and authorization events.

Payloads contain event-specific data. Universal event metadata is supplied
separately when decoding; actor and envelope metadata belongs to the enclosing
outbox message.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.auth_events import AuthorizationDenied, UserAuthenticated
from src.domain.enums.auth import Permission, Role
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_list, require_optional_str, require_positive_int, require_str


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
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "attempted_operation",
            "target_resource_type",
            "target_resource_id",
            "required_permissions",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        attempted_operation = AuthorizationOperation(
            require_str(payload["attempted_operation"], "attempted_operation")
        )
        target_resource_type = AuditResourceType(
            require_str(payload["target_resource_type"], "target_resource_type")
        )
        target_resource_id = require_optional_str(payload["target_resource_id"], "target_resource_id")
        raw_permissions = require_list(payload["required_permissions"], "required_permissions")

        permissions: list[Permission] = []
        for index, item in enumerate(raw_permissions):
            field_name = f"required_permissions[{index}]"
            name = require_str(item, field_name)

            try:
                permission = Permission[name]
            except KeyError as exc:
                raise ValueError(f"{field_name}: unknown permission name {name!r}") from exc

            permissions.append(permission)

        return AuthorizationDenied(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            attempted_operation=attempted_operation,
            target_resource_type=target_resource_type,
            target_resource_id=target_resource_id,
            required_permissions=tuple(permissions),
        )


class UserAuthenticatedEventPayloadCodec(EventPayloadCodec[UserAuthenticated]):
    """Encode and decode version-1 successful-authentication payloads.

    The exact required fields are a positive integer ``user_id``, string
    ``username``, and ``role`` encoded by enum value. Booleans, numeric strings,
    and floats are not valid identifiers. Username text is retained verbatim,
    without imposing account-creation rules or changing historical event data.

    Encoding expects correctly typed event fields. Decoding validates the
    payload and lets the event constructor validate universal metadata.
    """

    @property
    def event_class(self) -> type[UserAuthenticated]:
        """Return the concrete successful-authentication event class."""
        return UserAuthenticated

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_authenticated``."""
        return "user_authenticated"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserAuthenticated) -> JSONObject:
        """Serialize the event-specific fields into a fresh JSON object.

        Args:
            event: Version-1 successful-authentication event to serialize.

        Returns:
            Integer user ID, unmodified username, and role enum value. Event
            and envelope metadata are excluded.
        """
        return {
            "user_id": event.user_id,
            "username": event.username,
            "role": event.role.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> UserAuthenticated:
        """Validate a version-1 payload and restore its original metadata.

        Args:
            payload: JSON object containing exactly user_id, username, and role.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new successful-authentication event. Input data is not mutated;
            username text, including whitespace and case, is preserved.

        Raises:
            TypeError: If payload fields or supplied metadata have invalid
                runtime types, including a boolean, float, or string user ID.
            ValueError: If keys are missing or unexpected, user_id is not
                positive, role is unknown, or timestamps use the wrong time
                domain.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "user_id",
            "username",
            "role",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        user_id = require_positive_int(payload["user_id"], "user_id")
        username = require_str(payload["username"], "username")
        role = Role(require_str(payload["role"], "role"))

        return UserAuthenticated(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
            role=role,
        )
