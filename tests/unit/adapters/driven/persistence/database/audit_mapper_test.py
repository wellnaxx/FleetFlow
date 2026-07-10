"""Tests for Postgres audit row mapping."""

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.adapters.driven.persistence.database.mappers.audit import map_audit_record
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource

OCCURRED_AT = datetime(2025, 1, 1, 12, 0)
RECORDED_AT = datetime(2025, 1, 1, 12, 1, tzinfo=UTC)
CREATED_AT = datetime(2025, 1, 2, 12, 0, tzinfo=UTC)


class AuditMapperTests(unittest.TestCase):
    """Validate conversion from raw database rows to audit records."""

    def test_map_audit_record_converts_database_strings_to_enums(self) -> None:
        event_id = uuid4()
        envelope_id = uuid4()
        correlation_id = uuid4()
        causation_id = uuid4()

        record = map_audit_record(
            {
                "audit_id": 1,
                "event_id": event_id,
                "event_version": 2,
                "event_type": "PackageCreated",
                "occurred_at": OCCURRED_AT,
                "recorded_at": RECORDED_AT,
                "envelope_id": envelope_id,
                "correlation_id": correlation_id,
                "causation_id": causation_id,
                "source": "CLI",
                "actor_user_id": 10,
                "actor_username": "manager",
                "resource_type": "package",
                "resource_id": "20",
                "action": "created",
                "payload_json": {"package_id": "20"},
                "created_at": CREATED_AT,
            }
        )

        self.assertEqual(record.audit_id, 1)
        self.assertEqual(record.event_id, event_id)
        self.assertEqual(record.event_version, 2)
        self.assertEqual(record.envelope_id, envelope_id)
        self.assertEqual(record.correlation_id, correlation_id)
        self.assertEqual(record.causation_id, causation_id)
        self.assertEqual(record.source, EventSource.CLI)
        self.assertEqual(record.resource_type, AuditResourceType.PACKAGE)
        self.assertEqual(record.action, AuditAction.CREATED)
        self.assertEqual(record.payload_json, {"package_id": "20"})

    def test_map_audit_record_rejects_bool_actor_user_id(self) -> None:
        row = _row(actor_user_id=True)

        with self.assertRaisesRegex(TypeError, "actor_user_id: expected int or None"):
            map_audit_record(row)

    def test_map_audit_record_rejects_bool_event_version(self) -> None:
        row = _row(event_version=True)

        with self.assertRaisesRegex(TypeError, "event_version: expected int"):
            map_audit_record(row)

    def test_map_audit_record_rejects_invalid_enum_value(self) -> None:
        row = _row(action="missing")

        with self.assertRaises(ValueError):
            map_audit_record(row)

    def test_map_audit_record_rejects_invalid_payload_json(self) -> None:
        row = _row(payload_json={"bad": object()})

        with self.assertRaisesRegex(TypeError, "payload_json.bad"):
            map_audit_record(row)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "audit_id": 1,
        "event_id": uuid4(),
        "event_version": 2,
        "event_type": "PackageCreated",
        "occurred_at": OCCURRED_AT,
        "recorded_at": RECORDED_AT,
        "envelope_id": uuid4(),
        "correlation_id": uuid4(),
        "causation_id": None,
        "source": "CLI",
        "actor_user_id": 10,
        "actor_username": "manager",
        "resource_type": "package",
        "resource_id": "20",
        "action": "created",
        "payload_json": {"package_id": "20"},
        "created_at": CREATED_AT,
    }
    row.update(overrides)
    return row


if __name__ == "__main__":
    unittest.main()
