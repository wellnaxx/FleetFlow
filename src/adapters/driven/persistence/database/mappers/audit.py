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
from src.shared.validation import (
    require_datetime,
    require_int,
    require_optional_int,
    require_optional_str,
    require_optional_uuid,
    require_str,
    require_uuid,
)


class AuditRow(TypedDict):
    """Typed, validated representation of one persisted audit row."""

    audit_id: int
    event_id: UUID
    event_version: int
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
        event_version=typed["event_version"],
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

    Args:
        row: Raw dictionary returned by the database executor.

    Returns:
        Typed audit row containing validated values and parsed enums.

    Raises:
        KeyError: If a required audit column is absent.
        TypeError: If a column has an incompatible runtime type or invalid
            JSON payload shape.
        ValueError: If a persisted enum value is unknown.
    """
    audit_id = require_int(row["audit_id"], "audit_id")
    event_id = require_uuid(row["event_id"], "event_id")
    event_version = require_int(row["event_version"], "event_version")
    event_type = require_str(row["event_type"], "event_type")
    occurred_at = require_datetime(row["occurred_at"], "occurred_at")
    recorded_at = require_datetime(row["recorded_at"], "recorded_at")
    envelope_id = require_uuid(row["envelope_id"], "envelope_id")
    correlation_id = require_uuid(row["correlation_id"], "correlation_id")
    causation_id = require_optional_uuid(row["causation_id"], "causation_id")
    source = require_str(row["source"], "source")
    actor_user_id = require_optional_int(row["actor_user_id"], "actor_user_id")
    actor_username = require_optional_str(row["actor_username"], "actor_username")
    resource_type = require_str(row["resource_type"], "resource_type")
    resource_id = require_optional_str(row["resource_id"], "resource_id")
    action = require_str(row["action"], "action")
    payload_json = row["payload_json"]
    created_at = require_datetime(row["created_at"], "created_at")

    payload_json = require_json_object(payload_json, "payload_json")

    return AuditRow(
        audit_id=audit_id,
        event_id=event_id,
        event_version=event_version,
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
