"""Tests for audit-log record models."""

import math
import unittest
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast
from uuid import UUID, uuid4

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_record import AuditRecord, AuditRecordDraft, JSONObject


class AuditRecordDraftShould(unittest.TestCase):
    """Validate construction-time audit draft invariants."""

    def test_accept_valid_json_safe_payload(self) -> None:
        draft = AuditRecordDraft(
            **make_draft_kwargs(
                event_type=" PackageCreated ",
                actor_username=" Admin ",
                resource_id=" 42 ",
                payload_json={
                    "package_id": 42,
                    "labels": ["priority", None, True, 10.5],
                    "nested": {"route_id": "7"},
                },
            )
        )

        self.assertEqual(draft.event_type, "PackageCreated")
        self.assertEqual(draft.actor_username, "Admin")
        self.assertEqual(draft.resource_id, "42")
        self.assertEqual(draft.payload_json["nested"], {"route_id": "7"})

    def test_reject_invalid_identity_and_context_types(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
            ("event_id", "not-a-uuid", TypeError),
            ("occurred_at", "not-a-datetime", TypeError),
            ("source", "HTTP", TypeError),
            ("resource_type", "package", TypeError),
            ("action", "created", TypeError),
        )

        for field_name, value, expected_error in cases:
            with self.subTest(field_name=field_name):
                kwargs = make_draft_kwargs(**{field_name: cast(Any, value)})

                with self.assertRaises(expected_error):
                    AuditRecordDraft(**kwargs)

    def test_reject_invalid_positive_integer_fields(self) -> None:
        for value in (0, -1, True, "1"):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                AuditRecordDraft(**make_draft_kwargs(actor_user_id=cast(Any, value)))

    def test_require_business_occurrence_time_and_utc_recording_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "occurred_at must be timezone-naive"):
            AuditRecordDraft(
                **make_draft_kwargs(occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
            )

        for recorded_at in (
            datetime(2026, 1, 1, 12, 0, 1),
            datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone(timedelta(hours=2))),
        ):
            with self.subTest(recorded_at=recorded_at), self.assertRaises(ValueError):
                AuditRecordDraft(**make_draft_kwargs(recorded_at=recorded_at))

    def test_reject_invalid_event_version(self) -> None:
        for value in (0, -1, True, "2"):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                AuditRecordDraft(**make_draft_kwargs(event_version=cast(Any, value)))

    def test_reject_empty_string_fields(self) -> None:
        for field_name in ("event_type", "actor_username", "resource_id"):
            with self.subTest(field_name=field_name), self.assertRaises(ValueError):
                AuditRecordDraft(**make_draft_kwargs(**{field_name: "   "}))

    def test_reject_non_string_json_object_keys(self) -> None:
        with self.assertRaisesRegex(TypeError, "payload_json: expected JSON object keys as strings"):
            AuditRecordDraft(**make_draft_kwargs(payload_json=cast(JSONObject, {1: "bad"})))

    def test_reject_non_json_values(self) -> None:
        invalid_values: tuple[object, ...] = (
            datetime(2026, 1, 1, 12, 0),
            uuid4(),
            (1, 2),
        )

        for value in invalid_values:
            with self.subTest(value=type(value).__name__), self.assertRaises(TypeError):
                AuditRecordDraft(**make_draft_kwargs(payload_json={"value": cast(Any, value)}))

    def test_reject_non_finite_json_numbers(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "expected finite JSON number"):
                AuditRecordDraft(**make_draft_kwargs(payload_json={"value": value}))


class AuditRecordShould(unittest.TestCase):
    """Validate persisted audit-record metadata."""

    def test_accept_valid_persisted_record(self) -> None:
        record = AuditRecord(
            **make_draft_kwargs(
                audit_id=1,
                created_at=datetime(2026, 1, 1, 12, 0, 2, tzinfo=UTC),
            )
        )

        self.assertEqual(record.audit_id, 1)
        self.assertEqual(record.created_at, datetime(2026, 1, 1, 12, 0, 2, tzinfo=UTC))

    def test_reject_invalid_persisted_metadata(self) -> None:
        with self.assertRaises(ValueError):
            AuditRecord(
                **make_draft_kwargs(
                    audit_id=0,
                    created_at=datetime(2026, 1, 1, 12, 0, 2, tzinfo=UTC),
                )
            )

        with self.assertRaises(TypeError):
            AuditRecord(
                **make_draft_kwargs(
                    audit_id=1,
                    created_at=cast(Any, "not-a-datetime"),
                )
            )

    def test_require_utc_creation_time(self) -> None:
        for created_at in (
            datetime(2026, 1, 1, 12, 0, 2),
            datetime(2026, 1, 1, 12, 0, 2, tzinfo=timezone(timedelta(hours=-5))),
        ):
            with self.subTest(created_at=created_at), self.assertRaises(ValueError):
                AuditRecord(
                    **make_draft_kwargs(
                        audit_id=1,
                        created_at=created_at,
                    )
                )


def make_draft_kwargs(**overrides: object) -> dict[str, Any]:
    """Return valid audit-record construction kwargs with optional overrides."""
    kwargs: dict[str, Any] = {
        "event_id": UUID("11111111-1111-1111-1111-111111111111"),
        "event_version": 2,
        "event_type": "PackageCreated",
        "occurred_at": datetime(2026, 1, 1, 12, 0),
        "recorded_at": datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC),
        "envelope_id": UUID("22222222-2222-2222-2222-222222222222"),
        "correlation_id": UUID("33333333-3333-3333-3333-333333333333"),
        "causation_id": UUID("44444444-4444-4444-4444-444444444444"),
        "source": EventSource.HTTP,
        "actor_user_id": 7,
        "actor_username": "admin",
        "resource_type": AuditResourceType.PACKAGE,
        "resource_id": "42",
        "action": AuditAction.CREATED,
        "payload_json": {"package_id": 42},
    }
    kwargs.update(overrides)
    return kwargs
