"""Authentication, session termination, and token revocation outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.enums.user_login_rejection_reasons import UserLoginRejectionReason
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.auth_events import (
    UserAuthenticated,
    UserLoginRejected,
    UserSessionEnded,
    UserTokensRevoked,
)
from src.domain.enums.auth import Role
from src.shared.json_deserialization import parse_enum_value
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import (
    require_optional_positive_int,
    require_optional_str,
    require_positive_int,
    require_str,
)

_USER_AUTHENTICATED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "user_id",
    "username",
    "role",
])


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
        require_json_object_keys(payload, _USER_AUTHENTICATED_PAYLOAD_KEYS)

        user_id = require_positive_int(payload["user_id"], "user_id")
        username = require_str(payload["username"], "username")
        role = parse_enum_value(payload["role"], "role", Role)

        return UserAuthenticated(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
            role=role,
        )


_USER_LOGIN_REJECTED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["user_id", "username", "reason"])


class UserLoginRejectedEventPayloadCodec(EventPayloadCodec[UserLoginRejected]):
    """Encode and decode version-1 rejected-login payloads.

    All three keys are required, even when ``user_id`` or ``username`` is null.
    A present identifier must be a positive integer; username text is preserved
    verbatim. Reasons are serialized by enum value. The two nullable fields
    are independent, with no reason-specific combinations imposed by this codec.

    Encoding expects correctly typed event fields. Decoding validates payload
    fields and delegates universal metadata validation to the event constructor.
    """

    @property
    def event_class(self) -> type[UserLoginRejected]:
        """Return the concrete rejected-login event class."""
        return UserLoginRejected

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_login_rejected``."""
        return "user_login_rejected"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserLoginRejected) -> JSONObject:
        """Serialize rejected-login fields into a fresh JSON object.

        Args:
            event: Version-1 rejected-login event to serialize.

        Returns:
            Nullable integer user ID, nullable unmodified username, and the
            rejection reason's enum value. Event and envelope metadata are
            excluded; absent values remain explicit JSON nulls.
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
    ) -> UserLoginRejected:
        """Validate a version-1 payload and reconstruct the rejected login.

        Args:
            payload: JSON object containing exactly user_id, username, and reason.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new rejected-login event with the supplied metadata, nullable
            identity fields, and typed rejection reason. Input data is not
            mutated and username whitespace and case are preserved.

        Raises:
            TypeError: If a field or metadata value has an invalid runtime
                type, including a boolean, string, or float user ID.
            ValueError: If keys are missing or unexpected, a supplied user ID
                is not positive, reason is unknown, or timestamps use the
                wrong time domain.
        """
        require_json_object_keys(payload, _USER_LOGIN_REJECTED_PAYLOAD_KEYS)

        user_id = require_optional_positive_int(payload["user_id"], "user_id")
        username = require_optional_str(payload["username"], "username")
        reason = parse_enum_value(payload["reason"], "reason", UserLoginRejectionReason)

        return UserLoginRejected(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
            reason=reason,
        )


_USER_SESSION_ENDED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["user_id", "username"])


class UserSessionEndedEventPayloadCodec(EventPayloadCodec[UserSessionEnded]):
    """Encode and decode version-1 local-session-ended payloads.

    Exactly ``user_id`` and ``username`` identify the user whose local session
    ended. Both fields are required and non-null. IDs must be positive integers
    excluding booleans; username case and whitespace are preserved verbatim.
    Ending a local session is distinct from revoking outstanding tokens.

    Encoding expects correctly typed event fields. Decoding validates the
    payload and delegates universal metadata validation to the event constructor.
    Credentials, token data, and envelope metadata are excluded from the payload.
    """

    @property
    def event_class(self) -> type[UserSessionEnded]:
        """Return the concrete local-session-ended event class."""
        return UserSessionEnded

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_session_ended``."""
        return "user_session_ended"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserSessionEnded) -> JSONObject:
        """Serialize the ended session's user identity.

        Args:
            event: Version-1 local-session-ended event to serialize.

        Returns:
            A fresh JSON object containing integer user ID and unmodified
            username. Credentials, tokens, and event and envelope metadata
            are excluded.
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
    ) -> UserSessionEnded:
        """Validate a version-1 payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly user_id and username.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new session-ended event with the supplied metadata. Input data
            is not mutated; username text is preserved without normalization.

        Raises:
            TypeError: If fields or metadata have invalid runtime types,
                including null identity fields or a boolean, string, or float
                user ID.
            ValueError: If keys are missing or unexpected, user ID is not
                positive, or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _USER_SESSION_ENDED_PAYLOAD_KEYS)

        user_id = require_positive_int(payload["user_id"], "user_id")
        username = require_str(payload["username"], "username")

        return UserSessionEnded(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
        )


_USER_TOKENS_REVOKED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["user_id", "username", "reason"])


class UserTokensRevokedEventPayloadCodec(EventPayloadCodec[UserTokensRevoked]):
    """Encode and decode version-1 token-revocation confirmations.

    Exactly ``user_id``, ``username``, and ``reason`` describe the account whose
    outstanding tokens were invalidated. All fields are required and non-null.
    IDs must be positive integers excluding booleans; username text is preserved
    verbatim. Reasons use enum values. Token contents, credentials, and envelope
    metadata are excluded. Revocation is distinct from ending a local session.

    Encoding expects correctly typed event fields. Decoding validates the
    payload and delegates universal metadata validation to the event constructor.
    """

    @property
    def event_class(self) -> type[UserTokensRevoked]:
        """Return the concrete token-revocation event class."""
        return UserTokensRevoked

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``user_tokens_revoked``."""
        return "user_tokens_revoked"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: UserTokensRevoked) -> JSONObject:
        """Serialize the affected account and token-revocation reason.

        Args:
            event: Version-1 token-revocation event to serialize.

        Returns:
            A fresh JSON object containing integer user ID, unmodified username,
            and the reason's enum value. Credentials, tokens, and event and
            envelope metadata are excluded.
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
    ) -> UserTokensRevoked:
        """Validate a version-1 payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly user_id, username, and reason.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new token-revocation event with the supplied metadata and a typed
            reason. Input data is not mutated; username case and whitespace
            are preserved without normalization.

        Raises:
            TypeError: If fields or metadata have invalid runtime types,
                including null fields or a boolean, string, or float user ID.
            ValueError: If keys are missing or unexpected, user ID is not
                positive, reason is unknown, or timestamps use the wrong time
                domain.
        """
        require_json_object_keys(payload, _USER_TOKENS_REVOKED_PAYLOAD_KEYS)

        user_id = require_positive_int(payload["user_id"], "user_id")
        username = require_str(payload["username"], "username")
        reason = parse_enum_value(payload["reason"], "reason", TokenRevocationReason)

        return UserTokensRevoked(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            user_id=user_id,
            username=username,
            reason=reason,
        )
