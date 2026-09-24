"""User registration successes and rejections outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.user_registration_rejection_reasons import UserRegistrationRejectionReason
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.auth_events import UserRegistered, UserRegistrationRejected
from src.domain.enums.auth import Role
from src.shared.json_deserialization import parse_enum_value
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_optional_str, require_positive_int, require_str

_USER_REGISTERED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["user_id", "username", "role"])


class UserRegisteredEventPayloadCodec(EventPayloadCodec[UserRegistered]):
    """Encode and decode version-1 successful user-registration payloads.

    Exactly ``user_id``, ``username``, and ``role`` describe the created account.
    The ID must be a positive integer excluding booleans. Username text is
    retained verbatim without reapplying account-creation normalization or
    validation rules; roles use enum values. Credentials are excluded and actor
    identity belongs to envelope metadata.

    Encoding expects correctly typed event fields. Decoding validates the
    payload and delegates universal metadata validation to the event constructor.
    """

    @property
    def event_class(self) -> type[UserRegistered]:
        """Return the concrete successful-registration event class."""
        return UserRegistered

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_registered``."""
        return "user_registered"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserRegistered) -> JSONObject:
        """Serialize the created account's identity and role.

        Args:
            event: Version-1 user-registration event to serialize.

        Returns:
            A fresh JSON object containing integer user ID, unmodified username,
            and role enum value. Credentials and event and envelope metadata
            are excluded.
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
    ) -> UserRegistered:
        """Validate a version-1 payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly user_id, username, and role.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new registration event with a typed role and supplied metadata.
            Input data is not mutated; username case and whitespace are retained.

        Raises:
            TypeError: If fields or metadata have invalid runtime types,
                including null fields or a boolean, string, or float user ID.
            ValueError: If keys are missing or unexpected, the user ID is not
                positive, role is unknown, or timestamps use the wrong time
                domain.
        """
        require_json_object_keys(payload, _USER_REGISTERED_PAYLOAD_KEYS)

        user_id = require_positive_int(payload["user_id"], "user_id")
        username = require_str(payload["username"], "username")
        role = parse_enum_value(payload["role"], "role", Role)

        return UserRegistered(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
            role=role,
        )


_USER_REGISTRATION_REJECTED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["username", "reason"])


class UserRegistrationRejectedEventPayloadCodec(EventPayloadCodec[UserRegistrationRejected]):
    """Encode and decode version-1 rejected user-registration payloads.

    Exactly ``username`` and ``reason`` are required. Username may be null;
    supplied text is preserved, including blank values from invalid-username
    attempts. Reasons use enum values. No account ID, credentials, or actor
    metadata belongs in this payload.

    Encoding expects correctly typed event fields. Decoding validates payload
    fields and delegates universal metadata validation to the event constructor.
    """

    @property
    def event_class(self) -> type[UserRegistrationRejected]:
        """Return the concrete rejected-registration event class."""
        return UserRegistrationRejected

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_registration_rejected``."""
        return "user_registration_rejected"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserRegistrationRejected) -> JSONObject:
        """Serialize the attempted username and registration-rejection reason.

        Args:
            event: Version-1 rejected-registration event to serialize.

        Returns:
            A fresh JSON object containing nullable username and the reason's
            enum value. An absent username remains an explicit JSON null.
            Credentials and event and envelope metadata are excluded.
        """
        return {
            "username": event.username,
            "reason": event.reason.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> UserRegistrationRejected:
        """Validate a version-1 payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly username and reason.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new rejected-registration event with a nullable username and
            typed reason. Input data is not mutated; username case and
            whitespace are preserved without account-creation normalization.

        Raises:
            TypeError: If username is neither string nor null, reason is not
                a string, or supplied event metadata has an invalid type.
            ValueError: If keys are missing or unexpected, reason is unknown,
                or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _USER_REGISTRATION_REJECTED_PAYLOAD_KEYS)

        username = require_optional_str(payload["username"], "username")
        reason = parse_enum_value(payload["reason"], "reason", UserRegistrationRejectionReason)

        return UserRegistrationRejected(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            username=username,
            reason=reason,
        )
