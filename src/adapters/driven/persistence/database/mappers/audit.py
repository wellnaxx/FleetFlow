"""Map Postgres audit rows into application audit models."""

from datetime import datetime
from typing import TypedDict
from uuid import UUID

from src.adapters.driven.persistence.database.executor import RowDict
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_record import AuditRecord
from src.application.models.audit_validation import require_json_object
from src.shared.json_types import JSONObject


class AuditRow(TypedDict):
    """Typed, validated representation of one persisted audit row."""

    audit_id: int
    event_id: UUID
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    envelope_id: UUID
    correlation_id: UUID
    causation_id: UUID | None
    source: EventSource
    actor_user_id: int | None
    actor_username: str | None
    resource_type: AuditResourceType
    resource_id: str | None
    action: AuditAction
    payload_json: JSONObject
    created_at: datetime


def map_audit_record(row: RowDict) -> AuditRecord:
    """Map one database row into an ``AuditRecord``.

    Args:
        row: Dictionary returned by the database executor.

    Returns:
        Validated audit record model.

    Raises:
        KeyError: If a required audit column is missing.
        TypeError: If a column has an unexpected runtime type.
        ValueError: If a persisted enum value is unknown or a model invariant
            is violated.
    """
    typed = _as_audit_row(row)
    return AuditRecord(
        audit_id=typed["audit_id"],
        event_id=typed["event_id"],
        event_type=typed["event_type"],
        occurred_at=typed["occurred_at"],
        recorded_at=typed["recorded_at"],
        envelope_id=typed["envelope_id"],
        correlation_id=typed["correlation_id"],
        causation_id=typed["causation_id"],
        source=typed["source"],
        actor_user_id=typed["actor_user_id"],
        actor_username=typed["actor_username"],
        resource_type=typed["resource_type"],
        resource_id=typed["resource_id"],
        action=typed["action"],
        payload_json=typed["payload_json"],
        created_at=typed["created_at"],
    )


def _as_audit_row(row: RowDict) -> AuditRow:
    """Validate and normalize raw audit row values.

    PostgreSQL returns enum-backed audit fields as strings because the audit
    table stores normalized text values. This helper validates raw types,
    converts those strings back into application enums, and validates JSONB
    payload shape before constructing the typed row.
    """
    audit_id = row["audit_id"]
    event_id = row["event_id"]
    event_type = row["event_type"]
    occurred_at = row["occurred_at"]
    recorded_at = row["recorded_at"]
    envelope_id = row["envelope_id"]
    correlation_id = row["correlation_id"]
    causation_id = row["causation_id"]
    source = row["source"]
    actor_user_id = row["actor_user_id"]
    actor_username = row["actor_username"]
    resource_type = row["resource_type"]
    resource_id = row["resource_id"]
    action = row["action"]
    payload_json = row["payload_json"]
    created_at = row["created_at"]

    if not isinstance(audit_id, int) or isinstance(audit_id, bool):
        raise TypeError(f"audit_id: expected int, got {type(audit_id).__name__}")
    
    if not isinstance(event_id, UUID):
        raise TypeError(f"event_id: expected UUID, got {type(event_id).__name__}")
    
    if not isinstance(event_type, str):
        raise TypeError(f"event_type: expected str, got {type(event_type).__name__}")
    
    if not isinstance(occurred_at, datetime):
        raise TypeError(f"occurred_at: expected datetime, got {type(occurred_at).__name__}")
    
    if not isinstance(recorded_at, datetime):
        raise TypeError(f"recorded_at: expected datetime, got {type(recorded_at).__name__}")
    
    if not isinstance(envelope_id, UUID):
        raise TypeError(f"envelope_id: expected UUID, got {type(envelope_id).__name__}")
    
    if not isinstance(correlation_id, UUID):
        raise TypeError(f"correlation_id: expected UUID, got {type(correlation_id).__name__}")
    
    if not isinstance(causation_id, UUID) and causation_id is not None:
        raise TypeError(f"causation_id: expected UUID or None, got {type(causation_id).__name__}")
    
    if not isinstance(source, str):
        raise TypeError(f"source: expected str, got {type(source).__name__}")
    
    if (not isinstance(actor_user_id, int) or isinstance(actor_user_id, bool)) and actor_user_id is not None:
        raise TypeError(f"actor_user_id: expected int or None, got {type(actor_user_id).__name__}")
    
    if not isinstance(actor_username, str) and actor_username is not None:
        raise TypeError(f"actor_username: expected str or None, got {type(actor_username).__name__}")
    
    if not isinstance(resource_type, str):
        raise TypeError(f"resource_type: expected str, got {type(resource_type).__name__}")
    
    if not isinstance(resource_id, str) and resource_id is not None:
        raise TypeError(f"resource_id: expected str or None, got {type(resource_id).__name__}")
    
    if not isinstance(action, str):
        raise TypeError(f"action: expected str, got {type(action).__name__}")
    
    payload_json = require_json_object(payload_json, "payload_json")

    if not isinstance(created_at, datetime):
        raise TypeError(f"created_at: expected datetime, got {type(created_at).__name__}")
    
    return AuditRow(
        audit_id=audit_id,
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        envelope_id=envelope_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        source=EventSource(source),
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        resource_type=AuditResourceType(resource_type),
        resource_id=resource_id,
        action=AuditAction(action),
        payload_json=payload_json,
        created_at=created_at,
    )
