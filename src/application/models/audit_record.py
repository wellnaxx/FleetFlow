"""Audit-log records produced from serialized event envelopes.

Audit records are normalized, JSON-safe representations of published domain
and application events. Event-specific data is stored in ``payload_json`` after
serialization, while universal event and envelope metadata is stored in
dedicated columns.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object
from src.shared.validation import (
    require_enum,
    require_naive_datetime,
    require_non_empty_str,
    require_positive_int,
    require_utc_datetime,
    require_uuid,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditRecordDraft:
    """Write-side audit record before persistence metadata is assigned.

    Event handlers build drafts from event envelopes after event-specific
    payload serialization. The draft contains the durable event identity,
    envelope context, normalized audit descriptor fields, and JSON-safe event
    details.

    Attributes:
        event_id: Unique id of the original domain or application event.
        event_version: Positive version of the concrete event's serialized
            contract at the time the audit record was produced.
        event_type: Concrete event class name, e.g. ``PackageCreated``.
        occurred_at: Business timestamp carried by the event.
        recorded_at: Timestamp when FleetFlow recorded the event.
        envelope_id: Unique id of this publication envelope.
        correlation_id: Workflow/request id shared by related events.
        causation_id: Direct cause id, when one exists.
        source: Driving source that produced the event.
        actor_user_id: Authenticated actor id, when one exists.
        actor_username: Authenticated actor username, when one exists.
        resource_type: Normalized audited resource family.
        resource_id: Resource identifier normalized as text, when one exists.
        action: Normalized audited action.
        payload_json: Event-specific JSON-safe payload. Universal event and
            envelope metadata is stored in dedicated fields instead.
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
    resource_type: AuditResourceType
    resource_id: str | None = None
    action: AuditAction
    payload_json: JSONObject

    def __post_init__(self) -> None:
        """Validate and normalize audit draft fields.

        Raises:
            TypeError: If a field has an incompatible runtime type or the
                payload contains a non-JSON value.
            ValueError: If a positive integer, non-empty string, enum, or JSON
                number invariant is violated.
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
        require_enum(self.resource_type, "resource_type", AuditResourceType)
        if self.resource_id is not None:
            object.__setattr__(self, "resource_id", require_non_empty_str(self.resource_id, "resource_id"))
        require_enum(self.action, "action", AuditAction)
        object.__setattr__(self, "payload_json", require_json_object(self.payload_json, "payload_json"))


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditRecord(AuditRecordDraft):
    """Persisted audit record with repository-assigned storage metadata.

    Attributes:
        audit_id: Positive repository-assigned audit-row identity.
        created_at: UTC timestamp when the audit record was persisted.
    """

    audit_id: int
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate draft fields and persisted audit metadata.

        Raises:
            TypeError: If draft fields or persisted timestamps have invalid
                runtime types.
            ValueError: If draft invariants fail or ``audit_id`` is not positive.
        """
        super().__post_init__()
        require_positive_int(self.audit_id, "audit_id")
        require_utc_datetime(self.created_at, "created_at")
