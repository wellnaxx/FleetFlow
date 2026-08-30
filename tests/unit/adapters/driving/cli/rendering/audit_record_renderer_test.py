"""Tests for audit-record CLI rendering."""

import unittest
from datetime import UTC, datetime
from uuid import UUID

from src.adapters.driving.cli.rendering.audit_record_renderer import render_audit_record
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_record import AuditRecord
from src.shared.json_types import JSONObject


class AuditRecordRendererShould(unittest.TestCase):
    """Verify human-readable audit record formatting."""

    def test_render_key_record_fields_and_sorted_payload(self) -> None:
        record = make_audit_record(
            payload_json={"zeta": 2, "alpha": 1},
            actor_username="alice",
            resource_id="42",
        )

        output = render_audit_record(record)

        self.assertIn("Audit ID: 1", output)
        self.assertIn("Event version: 2", output)
        self.assertIn("Event type: PackageCreated", output)
        self.assertIn("Occurred at: 2026-01-01 12:00:00", output)
        self.assertIn("Recorded at: 2026-01-01 12:00:01+00:00", output)
        self.assertIn("Source: CLI", output)
        self.assertIn("Actor's user ID: 7", output)
        self.assertIn("Actor's username: alice", output)
        self.assertIn("Resource type: package", output)
        self.assertIn("Resource ID: 42", output)
        self.assertIn("Action: created", output)
        self.assertIn('"alpha": 1', output)
        self.assertLess(output.index('"alpha": 1'), output.index('"zeta": 2'))
        self.assertIn("Created at: 2026-01-01 12:00:02+00:00", output)

    def test_render_optional_fields_as_not_available(self) -> None:
        record = make_audit_record(
            causation_id=None,
            actor_user_id=None,
            actor_username=None,
            resource_id=None,
        )

        output = render_audit_record(record)

        self.assertIn("Causation ID: N/A", output)
        self.assertIn("Actor's user ID: N/A", output)
        self.assertIn("Actor's username: N/A", output)
        self.assertIn("Resource ID: N/A", output)


def make_audit_record(
    *,
    causation_id: UUID | None = UUID("44444444-4444-4444-4444-444444444444"),
    actor_user_id: int | None = 7,
    actor_username: str | None = "admin",
    resource_id: str | None = "42",
    payload_json: JSONObject | None = None,
) -> AuditRecord:
    """Build a valid audit record for renderer tests."""
    return AuditRecord(
        event_id=UUID("11111111-1111-1111-1111-111111111111"),
        event_version=2,
        event_type="PackageCreated",
        occurred_at=datetime(2026, 1, 1, 12, 0, 0, 123),
        recorded_at=datetime(2026, 1, 1, 12, 0, 1, 456, tzinfo=UTC),
        envelope_id=UUID("22222222-2222-2222-2222-222222222222"),
        correlation_id=UUID("33333333-3333-3333-3333-333333333333"),
        causation_id=causation_id,
        source=EventSource.CLI,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        resource_type=AuditResourceType.PACKAGE,
        resource_id=resource_id,
        action=AuditAction.CREATED,
        payload_json=payload_json or {"package_id": 42},
        audit_id=1,
        created_at=datetime(2026, 1, 1, 12, 0, 2, 789, tzinfo=UTC),
    )
