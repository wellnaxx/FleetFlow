"""Validated write-side and persisted transactional-outbox messages.

The models preserve event and envelope metadata until an asynchronous worker
publishes the event. Business occurrence time remains naive app-local time;
recording and outbox lifecycle timestamps are UTC-aware.

The dataclasses are frozen only at the attribute level. ``event_payload_json``
is deliberately retained as the project's mutable ``JSONObject`` contract and
is shallow-copied during validation. Nested JSON containers are not frozen.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.application.enums.event_sources import EventSource
from src.application.enums.outbox_failures import OutboxFailureCategory
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object
from src.shared.validation import (
    require_enum,
    require_naive_datetime,
    require_non_empty_str,
    require_non_negative_int,
    require_optional_utc_datetime,
    require_optional_uuid,
    require_positive_int,
    require_utc_datetime,
    require_uuid,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class OutboxMessageDraft:
    """Write-side outbox message before persistence assigns delivery state.

    A draft is normally created from an event envelope in the same transaction
    as the application state change. It carries only durable event data; row
    identity, retry state, leases, and publication timestamps belong to
    :class:`OutboxMessage`.

    Although this dataclass is frozen, its JSON payload remains mutable. The
    constructor validates the complete JSON graph and stores a shallow copy of
    the top-level dictionary.

    Attributes:
        event_id: Unique identity of the event being published.
        event_version: Positive version of the concrete event contract.
        event_type: Non-empty concrete event class name.
        occurred_at: Naive app-local time when the represented fact occurred.
        recorded_at: UTC time when FleetFlow recorded the event.
        envelope_id: Unique identity of the publication envelope.
        correlation_id: Workflow identity shared by related messages.
        causation_id: Identity of the direct cause, when available.
        source: Driving adapter or process that produced the event.
        actor_user_id: Positive authenticated actor identity, when available.
        actor_username: Non-empty actor username, when available.
        event_payload_json: JSON-safe event-specific payload. Universal event
            and envelope metadata is stored in dedicated fields.
    """

    event_id: UUID
    event_version: int
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    envelope_id: UUID
    correlation_id: UUID
    causation_id: UUID | None = None
    source: EventSource
    actor_user_id: int | None = None
    actor_username: str | None = None
    event_payload_json: JSONObject

    def __post_init__(self) -> None:
        """Validate and normalize event and envelope metadata.

        String fields are stripped, and the top-level payload dictionary is
        shallow-copied after recursive JSON validation.

        Raises:
            TypeError: If a field has an incompatible runtime type, an enum is
                supplied as a raw string, or the payload graph is not JSON-safe.
            ValueError: If an identifier version is not positive, a required
                string is blank, or a timestamp uses the wrong time domain.
        """
        require_uuid(self.event_id, "event_id")
        require_positive_int(self.event_version, "event_version")
        object.__setattr__(self, "event_type", require_non_empty_str(self.event_type, "event_type"))
        require_naive_datetime(self.occurred_at, "occurred_at")
        require_utc_datetime(self.recorded_at, "recorded_at")
        require_uuid(self.envelope_id, "envelope_id")
        require_uuid(self.correlation_id, "correlation_id")
        if self.causation_id is not None:
            require_uuid(self.causation_id, "causation_id")
        require_enum(self.source, "source", EventSource)
        if self.actor_user_id is not None:
            require_positive_int(self.actor_user_id, "actor_user_id")
        if self.actor_username is not None:
            object.__setattr__(
                self,
                "actor_username",
                require_non_empty_str(self.actor_username, "actor_username"),
            )
        object.__setattr__(
            self,
            "event_payload_json",
            require_json_object(self.event_payload_json, "event_payload_json"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class OutboxMessage(OutboxMessageDraft):
    """Persisted outbox message with delivery and retry state.

    An unpublished row may be immediately available, delayed until
    ``available_at``, temporarily leased through ``claim_token`` and
    ``claimed_until``, or carry details from its most recent failed attempt. A
    published row is terminal: it has a positive attempt count and no active
    claim or failure metadata.

    Attributes:
        outbox_id: Positive repository-assigned row identity.
        created_at: UTC timestamp when the row was inserted.
        available_at: Earliest UTC timestamp at which processing may begin.
        attempt_count: Number of processing attempts started. Claiming a row
            increments this value before returning it to a worker.
        claimed_until: UTC lease expiry for an active worker claim, if any.
        claim_token: Opaque ownership token for an active worker claim. It
            prevents a worker with an expired lease from acknowledging a row
            subsequently claimed by another worker.
        published_at: UTC timestamp of successful publication, if complete.
        failure_category: Machine-readable category of the latest failure.
        last_error: Stripped diagnostic text for the latest failure. It is not
            an enum because concrete exception details remain operational data.

    Notes:
        ``claim_token`` and ``claimed_until`` are either both present or both
        absent. ``failure_category`` and ``last_error`` follow the same paired
        invariant. Failure and publication metadata require at least one
        attempt. Published messages cannot remain claimed or failed.
    """

    outbox_id: int
    created_at: datetime
    available_at: datetime
    attempt_count: int
    claimed_until: datetime | None
    claim_token: UUID | None
    published_at: datetime | None
    failure_category: OutboxFailureCategory | None
    last_error: str | None

    def __post_init__(self) -> None:
        """Validate draft metadata and persisted outbox lifecycle state.

        Raises:
            TypeError: If an inherited field or lifecycle field has an
                incompatible runtime type, including raw failure-category
                strings.
            ValueError: If timestamps are not UTC or are out of lifecycle
                order, counters violate their numeric invariants, failure
                fields are incomplete, or terminal publication state retains
                a claim or failure.
        """
        super().__post_init__()
        require_positive_int(self.outbox_id, "outbox_id")
        created_at = require_utc_datetime(self.created_at, "created_at")
        available_at = require_utc_datetime(self.available_at, "available_at")
        attempt_count = require_non_negative_int(self.attempt_count, "attempt_count")
        claimed_until = require_optional_utc_datetime(self.claimed_until, "claimed_until")
        claim_token = require_optional_uuid(self.claim_token, "claim_token")
        published_at = require_optional_utc_datetime(self.published_at, "published_at")
        has_failure = self.failure_category is not None

        if (claimed_until is not None) != (claim_token is not None):
            raise ValueError("claim_token and claimed_until must either both be provided or both be None.")
        if claim_token is not None and attempt_count == 0:
            raise ValueError("attempt_count must be positive when claim information is present.")

        if self.failure_category is not None:
            require_enum(
                self.failure_category,
                "failure_category",
                OutboxFailureCategory,
            )

        if has_failure != (self.last_error is not None):
            raise ValueError("failure_category and last_error must either both be provided or both be None.")

        if has_failure:
            object.__setattr__(
                self,
                "last_error",
                require_non_empty_str(self.last_error, "last_error"),
            )
            if attempt_count == 0:
                raise ValueError("attempt_count must be positive when failure information is present.")

        if published_at is not None:
            if attempt_count == 0:
                raise ValueError("attempt_count must be positive when published_at is present.")
            if claimed_until is not None:
                raise ValueError("claim information must be cleared when published_at is present.")
            if has_failure:
                raise ValueError("failure information must be cleared when published_at is present.")

        _require_not_before(available_at, created_at, "available_at", "created_at")
        if claimed_until is not None:
            _require_not_before(claimed_until, available_at, "claimed_until", "available_at")
        if published_at is not None:
            _require_not_before(published_at, available_at, "published_at", "available_at")


def _require_not_before(
    value: datetime,
    lower_bound: datetime,
    field_name: str,
    lower_bound_name: str,
) -> None:
    """Require two comparable datetimes ordered from lower bound to value.

    Args:
        value: Timestamp that must not precede ``lower_bound``.
        lower_bound: Earliest permitted timestamp.
        field_name: Name of ``value`` used in validation messages.
        lower_bound_name: Name of ``lower_bound`` used in validation messages.

    Raises:
        ValueError: If ``value`` precedes ``lower_bound``.
    """
    if value < lower_bound:
        raise ValueError(f"{field_name} must be after or equal to {lower_bound_name}.")
