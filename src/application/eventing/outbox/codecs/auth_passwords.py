"""Own-password changes and administrative password resets outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.user_password_change_rejection_reasons import UserPasswordChangeRejectionReason
from src.application.enums.user_password_reset_rejection_reasons import UserPasswordResetRejectionReason
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.auth_events import (
    UserPasswordChanged,
    UserPasswordChangeRejected,
    UserPasswordReset,
    UserPasswordResetRejected,
)
from src.shared.json_deserialization import parse_enum_value
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import (
    require_optional_positive_int,
    require_optional_str,
    require_positive_int,
    require_str,
)

_USER_PASSWORD_CHANGED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["user_id", "username"])


class UserPasswordChangedEventPayloadCodec(EventPayloadCodec[UserPasswordChanged]):
    """Encode and decode version-1 password-change confirmation payloads.

    Exactly ``user_id`` and ``username`` are required. The identifier must be
    a positive integer, excluding booleans; the username is a non-null string
    preserved verbatim, including case and whitespace. Passwords and password
    hashes are not part of the event or its serialized payload.

    Encoding expects correctly typed event fields. Decoding validates payload
    fields and delegates universal metadata validation to the event constructor.
    """

    @property
    def event_class(self) -> type[UserPasswordChanged]:
        """Return the concrete successful password-change event class."""
        return UserPasswordChanged

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_password_changed``."""
        return "user_password_changed"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserPasswordChanged) -> JSONObject:
        """Serialize the affected user's identity into a fresh JSON object.

        Args:
            event: Version-1 password-change confirmation to serialize.

        Returns:
            Integer user ID and unmodified username. No credentials or event
            and envelope metadata are included.
        """
        return {
            "user_id": event.user_id,
            "username": event.username,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> UserPasswordChanged:
        """Validate a version-1 payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly user_id and username.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new password-changed event with the supplied metadata. Input data
            is not mutated and username text is preserved without normalization.

        Raises:
            TypeError: If a field or metadata value has an invalid runtime
                type, including null identity fields or a boolean, string,
                or float user ID.
            ValueError: If keys are missing or unexpected, the user ID is not
                positive, or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _USER_PASSWORD_CHANGED_PAYLOAD_KEYS)

        user_id = require_positive_int(payload["user_id"], "user_id")
        username = require_str(payload["username"], "username")

        return UserPasswordChanged(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
        )


_USER_PASSWORD_CHANGE_REJECTED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "user_id",
    "username",
    "reason",
])


class UserPasswordChangeRejectedEventPayloadCodec(EventPayloadCodec[UserPasswordChangeRejected]):
    """Encode and decode version-1 rejected password-change payloads.

    Exactly ``user_id``, ``username``, and ``reason`` are required. Identity
    fields may independently be null; a supplied ID must be a positive integer.
    Username text is preserved, including blank values associated with an
    invalid-username rejection. Reasons use enum values. Passwords and hashes
    are excluded.

    Encoding expects correctly typed event fields. Decoding validates payload
    fields and delegates universal metadata validation to the event constructor.
    """

    @property
    def event_class(self) -> type[UserPasswordChangeRejected]:
        """Return the concrete rejected password-change event class."""
        return UserPasswordChangeRejected

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_password_change_rejected``."""
        return "user_password_change_rejected"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserPasswordChangeRejected) -> JSONObject:
        """Serialize the affected identity and rejection reason.

        Args:
            event: Version-1 rejected password-change event to serialize.

        Returns:
            A fresh JSON object containing the nullable user ID and username
            and reason enum value. Nulls are explicit; credentials and event
            and envelope metadata are excluded.
        """
        return {
            "user_id": event.user_id,
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
    ) -> UserPasswordChangeRejected:
        """Validate a version-1 payload and restore the original event metadata.

        Args:
            payload: JSON object containing exactly user_id, username, and reason.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new rejected password-change event with nullable identity fields
            and a typed reason. Payload data is not mutated and username case
            and whitespace are retained.

        Raises:
            TypeError: If fields or metadata have invalid runtime types,
                including a boolean, string, or float user ID.
            ValueError: If keys are missing or unexpected, a supplied user ID
                is not positive, reason is unknown, or timestamps use the
                wrong time domain.
        """
        require_json_object_keys(payload, _USER_PASSWORD_CHANGE_REJECTED_PAYLOAD_KEYS)

        user_id = require_optional_positive_int(payload["user_id"], "user_id")
        username = require_optional_str(payload["username"], "username")
        reason = parse_enum_value(payload["reason"], "reason", UserPasswordChangeRejectionReason)

        return UserPasswordChangeRejected(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
            reason=reason,
        )


_USER_PASSWORD_RESET_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["user_id", "username"])


class UserPasswordResetEventPayloadCodec(EventPayloadCodec[UserPasswordReset]):
    """Encode and decode version-1 administrator password-reset confirmations.

    Exactly ``user_id`` and ``username`` identify the account whose password
    was reset. Both are required and non-null; the ID must be a positive
    integer excluding booleans. Username case and whitespace are preserved.
    Administrator identity belongs to the envelope. Passwords and hashes are
    not part of this payload.

    Encoding expects correctly typed event fields. Decoding validates payload
    fields and delegates universal metadata validation to the event constructor.
    """

    @property
    def event_class(self) -> type[UserPasswordReset]:
        """Return the concrete successful password-reset event class."""
        return UserPasswordReset

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_password_reset``."""
        return "user_password_reset"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserPasswordReset) -> JSONObject:
        """Serialize the reset account's identity into a fresh JSON object.

        Args:
            event: Version-1 password-reset confirmation to serialize.

        Returns:
            Integer user ID and unmodified username. Credentials and event
            and envelope metadata are excluded.
        """
        return {
            "user_id": event.user_id,
            "username": event.username,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> UserPasswordReset:
        """Validate a version-1 payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly user_id and username.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new password-reset event with the supplied metadata. Input data
            is not mutated and username text is retained without normalization.

        Raises:
            TypeError: If a field or metadata value has an invalid runtime
                type, including null identity fields or a boolean, string,
                or float user ID.
            ValueError: If keys are missing or unexpected, the user ID is not
                positive, or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _USER_PASSWORD_RESET_PAYLOAD_KEYS)

        user_id = require_positive_int(payload["user_id"], "user_id")
        username = require_str(payload["username"], "username")

        return UserPasswordReset(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
        )


_USER_PASSWORD_RESET_REJECTED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "user_id",
    "username",
    "reason",
])


class UserPasswordResetRejectedEventPayloadCodec(EventPayloadCodec[UserPasswordResetRejected]):
    """Encode and decode version-1 administrator password-reset rejections.

    Exactly ``user_id``, ``username``, and ``reason`` are required. The identity
    fields describe the target account and may independently be null. A supplied
    ID must be a positive integer excluding booleans. Username text is retained,
    including blank values associated with invalid-username failures. Reasons
    use enum values, with no reason-specific identity combinations imposed here.

    Administrator identity belongs to the envelope. Credentials are excluded.
    Encoding expects correctly typed fields; decoding validates the payload
    and delegates universal metadata validation to the event constructor.
    """

    @property
    def event_class(self) -> type[UserPasswordResetRejected]:
        """Return the concrete rejected password-reset event class."""
        return UserPasswordResetRejected

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_password_reset_rejected``."""
        return "user_password_reset_rejected"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserPasswordResetRejected) -> JSONObject:
        """Serialize the target account and reset-rejection reason.

        Args:
            event: Version-1 rejected password-reset event to serialize.

        Returns:
            A fresh JSON object with nullable user ID and username and the
            reason enum value. Nulls remain explicit; credentials and event
            and envelope metadata are excluded.
        """
        return {
            "user_id": event.user_id,
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
    ) -> UserPasswordResetRejected:
        """Validate a version-1 payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly user_id, username, and reason.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new reset-rejected event with nullable target identity and a typed
            reason. Input data is not mutated and username case and whitespace
            are preserved.

        Raises:
            TypeError: If a field or metadata value has an invalid runtime
                type, including a boolean, string, or float user ID.
            ValueError: If keys are missing or unexpected, a supplied user ID
                is not positive, reason is unknown, or timestamps use the
                wrong time domain.
        """
        require_json_object_keys(payload, _USER_PASSWORD_RESET_REJECTED_PAYLOAD_KEYS)

        user_id = require_optional_positive_int(payload["user_id"], "user_id")
        username = require_optional_str(payload["username"], "username")
        reason = parse_enum_value(payload["reason"], "reason", UserPasswordResetRejectionReason)

        return UserPasswordResetRejected(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
            reason=reason,
        )
