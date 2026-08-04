"""CLI rendering for audit-log records."""

import json

from src.application.models.audit_record import AuditRecord


def render_audit_record(audit_record: AuditRecord) -> str:
    """Return a human-readable audit record summary.

    Args:
        audit_record: Persisted audit record to render.

    Returns:
        Multi-line audit record description for CLI display.
    """
    return "\n".join([
        f"Audit ID: {audit_record.audit_id}",
        f"Event ID: {audit_record.event_id}",
        f"Event version: {audit_record.event_version}",
        f"Event type: {audit_record.event_type}",
        f"Occurred at: {audit_record.occurred_at.replace(microsecond=0).isoformat(' ')}",
        f"Recorded at: {audit_record.recorded_at.replace(microsecond=0).isoformat(' ')}",
        f"Envelope ID: {audit_record.envelope_id}",
        f"Correlation ID: {audit_record.correlation_id}",
        f"Causation ID: {audit_record.causation_id if audit_record.causation_id is not None else 'N/A'}",
        f"Source: {audit_record.source.value}",
        f"Actor's user ID: {audit_record.actor_user_id if audit_record.actor_user_id is not None else 'N/A'}",
        f"Actor's username: {username if (username := audit_record.actor_username) is not None else 'N/A'}",
        f"Resource type: {audit_record.resource_type.value}",
        f"Resource ID: {audit_record.resource_id if audit_record.resource_id is not None else 'N/A'}",
        f"Action: {audit_record.action.value}",
        f"Payload:\n{json.dumps(audit_record.payload_json, indent=2, sort_keys=True)}",
        f"Created at: {audit_record.created_at.replace(microsecond=0).isoformat(' ')}",
    ])
