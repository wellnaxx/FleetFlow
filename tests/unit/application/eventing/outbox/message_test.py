"""Tests for transactional-outbox message contracts and lifecycle states."""

import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from src.application.enums.event_sources import EventSource
from src.application.enums.outbox_failures import OutboxFailureCategory
from src.application.eventing.outbox.message import OutboxMessage, OutboxMessageDraft

OCCURRED_AT = datetime(2026, 8, 30, 12, 0)
RECORDED_AT = datetime(2026, 8, 30, 9, 0, tzinfo=UTC)
CREATED_AT = RECORDED_AT + timedelta(seconds=1)
EVENT_ID = UUID("11111111-1111-1111-1111-111111111111")
ENVELOPE_ID = UUID("22222222-2222-2222-2222-222222222222")
CORRELATION_ID = UUID("33333333-3333-3333-3333-333333333333")
CAUSATION_ID = UUID("44444444-4444-4444-4444-444444444444")


class OutboxMessageDraftShould(unittest.TestCase):
    """Validate event metadata before persistence assigns outbox state."""

    def test_accept_normalize_and_retain_all_supported_event_metadata(self) -> None:
        payload = {
            "none": None,
            "text": "priority",
            "boolean": True,
            "integer": 7,
            "number": 1.25,
            "items": [1, "two", False, None, {"nested": "value"}],
        }

        draft = OutboxMessageDraft(
            **make_draft_kwargs(
                event_type=" PackageCreated ",
                actor_username=" Alice ",
                event_payload_json=payload,
            )
        )

        self.assertEqual(draft.event_type, "PackageCreated")
        self.assertEqual(draft.actor_username, "Alice")
        self.assertEqual(draft.event_payload_json, payload)
        self.assertIsNot(draft.event_payload_json, payload)
        self.assertEqual(draft.causation_id, CAUSATION_ID)

    def test_accept_absent_optional_envelope_metadata(self) -> None:
        draft = OutboxMessageDraft(
            **make_draft_kwargs(
                causation_id=None,
                actor_user_id=None,
                actor_username=None,
            )
        )

        self.assertIsNone(draft.causation_id)
        self.assertIsNone(draft.actor_user_id)
        self.assertIsNone(draft.actor_username)

    def test_be_attribute_frozen_while_retaining_mutable_json_payload(self) -> None:
        payload = {"package_id": 42}
        draft = OutboxMessageDraft(**make_draft_kwargs(event_payload_json=payload))

        with self.assertRaises(FrozenInstanceError):
            draft.event_type = "OtherEvent"  # type: ignore[reportAttributeAccessIssue]

        payload["later"] = True
        self.assertNotIn("later", draft.event_payload_json)
        draft.event_payload_json["local"] = True
        self.assertTrue(draft.event_payload_json["local"])

    def test_require_uuid_event_and_envelope_identifiers(self) -> None:
        for field_name in ("event_id", "envelope_id", "correlation_id", "causation_id"):
            with self.subTest(field_name=field_name), self.assertRaisesRegex(TypeError, field_name):
                OutboxMessageDraft(**make_draft_kwargs(**{field_name: "not-a-uuid"}))

    def test_require_positive_event_version(self) -> None:
        for value in (0, -1, True, "1", None):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                OutboxMessageDraft(**make_draft_kwargs(event_version=value))

    def test_require_non_empty_string_metadata(self) -> None:
        for field_name in ("event_type", "actor_username"):
            for value in ("", "   "):
                with (
                    self.subTest(field_name=field_name, value=value),
                    self.assertRaisesRegex(ValueError, field_name),
                ):
                    OutboxMessageDraft(**make_draft_kwargs(**{field_name: value}))

            with self.subTest(field_name=field_name, value=7), self.assertRaisesRegex(
                TypeError, field_name
            ):
                OutboxMessageDraft(**make_draft_kwargs(**{field_name: 7}))

    def test_require_naive_occurrence_and_utc_recording_timestamps(self) -> None:
        invalid_cases = (
            ("occurred_at", "not-a-datetime", TypeError),
            ("occurred_at", OCCURRED_AT.replace(tzinfo=UTC), ValueError),
            ("recorded_at", "not-a-datetime", TypeError),
            ("recorded_at", RECORDED_AT.replace(tzinfo=None), ValueError),
            (
                "recorded_at",
                RECORDED_AT.astimezone(timezone(timedelta(hours=2))),
                ValueError,
            ),
        )

        for field_name, value, error_type in invalid_cases:
            with self.subTest(field_name=field_name, value=value), self.assertRaises(error_type):
                OutboxMessageDraft(**make_draft_kwargs(**{field_name: value}))

    def test_require_event_source_enum_instance(self) -> None:
        for value in ("HTTP", "http", None):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "expected EventSource"):
                OutboxMessageDraft(**make_draft_kwargs(source=value))

    def test_require_positive_optional_actor_identifier(self) -> None:
        for value in (0, -1, True, "7"):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                OutboxMessageDraft(**make_draft_kwargs(actor_user_id=value))

    def test_require_payload_to_be_a_json_object_with_string_keys(self) -> None:
        invalid_objects: tuple[object, ...] = (None, [], "payload", 1)
        for value in invalid_objects:
            with self.subTest(value=value), self.assertRaisesRegex(
                TypeError, "event_payload_json: expected JSON object"
            ):
                OutboxMessageDraft(**make_draft_kwargs(event_payload_json=value))

        with self.assertRaisesRegex(TypeError, "keys as strings"):
            OutboxMessageDraft(**make_draft_kwargs(event_payload_json={1: "invalid"}))

    def test_reject_non_json_payload_values_at_any_depth(self) -> None:
        invalid_values = (
            datetime(2026, 1, 1),
            uuid4(),
            (1, 2),
            b"bytes",
            {"set"},
        )

        for value in invalid_values:
            payload = {"nested": [{"value": value}]}
            with self.subTest(value=type(value).__name__), self.assertRaisesRegex(
                TypeError, r"event_payload_json\.nested\[0\]\.value"
            ):
                OutboxMessageDraft(**make_draft_kwargs(event_payload_json=payload))

    def test_reject_non_finite_json_numbers_at_any_depth(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "finite JSON number"):
                OutboxMessageDraft(
                    **make_draft_kwargs(event_payload_json={"nested": [value]})
                )


class OutboxMessageShould(unittest.TestCase):
    """Validate persisted delivery state and lifecycle timestamps."""

    def test_accept_immediately_available_message(self) -> None:
        message = OutboxMessage(**make_message_kwargs())

        self.assertEqual(message.outbox_id, 1)
        self.assertEqual(message.available_at, CREATED_AT)
        self.assertEqual(message.attempt_count, 0)
        self.assertIsNone(message.claimed_until)
        self.assertIsNone(message.published_at)
        self.assertIsNone(message.failure_category)
        self.assertIsNone(message.last_error)

    def test_accept_delayed_unattempted_message(self) -> None:
        available_at = CREATED_AT + timedelta(minutes=5)

        message = OutboxMessage(**make_message_kwargs(available_at=available_at))

        self.assertEqual(message.available_at, available_at)
        self.assertEqual(message.attempt_count, 0)

    def test_accept_active_claim_at_or_after_availability(self) -> None:
        available_at = CREATED_AT + timedelta(minutes=5)

        for claimed_until in (available_at, available_at + timedelta(minutes=1)):
            with self.subTest(claimed_until=claimed_until):
                message = OutboxMessage(
                    **make_message_kwargs(
                        available_at=available_at,
                        claimed_until=claimed_until,
                    )
                )
                self.assertEqual(message.claimed_until, claimed_until)

    def test_accept_each_failed_message_category_and_normalize_error(self) -> None:
        for category in OutboxFailureCategory:
            with self.subTest(category=category):
                message = OutboxMessage(
                    **make_message_kwargs(
                        attempt_count=1,
                        failure_category=category,
                        last_error=" broker unavailable ",
                    )
                )
                self.assertIs(message.failure_category, category)
                self.assertEqual(message.last_error, "broker unavailable")

    def test_accept_published_terminal_message_at_or_after_availability(self) -> None:
        available_at = CREATED_AT + timedelta(minutes=5)

        for published_at in (available_at, available_at + timedelta(seconds=1)):
            with self.subTest(published_at=published_at):
                message = OutboxMessage(
                    **make_message_kwargs(
                        available_at=available_at,
                        attempt_count=1,
                        published_at=published_at,
                    )
                )
                self.assertEqual(message.published_at, published_at)

    def test_require_positive_outbox_identifier(self) -> None:
        for value in (0, -1, True, "1", None):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                OutboxMessage(**make_message_kwargs(outbox_id=value))

    def test_require_non_negative_attempt_count(self) -> None:
        for value in (-1, True, 1.5, "1", None):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                OutboxMessage(**make_message_kwargs(attempt_count=value))

    def test_require_utc_lifecycle_timestamps(self) -> None:
        for field_name in ("created_at", "available_at", "claimed_until", "published_at"):
            invalid_values = (
                "not-a-datetime",
                CREATED_AT.replace(tzinfo=None),
                CREATED_AT.astimezone(timezone(timedelta(hours=-4))),
            )
            for value in invalid_values:
                overrides: dict[str, object] = {field_name: value}
                if field_name == "published_at":
                    overrides["attempt_count"] = 1

                with self.subTest(field_name=field_name, value=value), self.assertRaises(
                    (TypeError, ValueError)
                ):
                    OutboxMessage(**make_message_kwargs(**overrides))

    def test_reject_lifecycle_timestamps_before_their_lower_bound(self) -> None:
        available_at = CREATED_AT + timedelta(minutes=5)
        cases = (
            {"available_at": CREATED_AT - timedelta(seconds=1)},
            {
                "available_at": available_at,
                "claimed_until": available_at - timedelta(seconds=1),
            },
            {
                "available_at": available_at,
                "attempt_count": 1,
                "published_at": available_at - timedelta(seconds=1),
            },
        )

        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, "must be after"):
                OutboxMessage(**make_message_kwargs(**overrides))

    def test_require_failure_category_and_error_together(self) -> None:
        cases = (
            {"attempt_count": 1, "failure_category": OutboxFailureCategory.PUBLICATION},
            {"attempt_count": 1, "last_error": "broker unavailable"},
        )

        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, "both"):
                OutboxMessage(**make_message_kwargs(**overrides))

    def test_reject_invalid_failure_category_runtime_type(self) -> None:
        with self.assertRaisesRegex(TypeError, "expected OutboxFailureCategory"):
            OutboxMessage(
                **make_message_kwargs(
                    attempt_count=1,
                    failure_category="publication",
                    last_error="broker unavailable",
                )
            )

    def test_require_non_empty_string_failure_diagnostics(self) -> None:
        for value in ("", "   "):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "last_error"):
                OutboxMessage(
                    **make_message_kwargs(
                        attempt_count=1,
                        failure_category=OutboxFailureCategory.PUBLICATION,
                        last_error=value,
                    )
                )

        with self.assertRaisesRegex(TypeError, "last_error"):
            OutboxMessage(
                **make_message_kwargs(
                    attempt_count=1,
                    failure_category=OutboxFailureCategory.PUBLICATION,
                    last_error=7,
                )
            )

    def test_require_attempt_for_failed_or_published_state(self) -> None:
        cases = (
            {
                "failure_category": OutboxFailureCategory.PUBLICATION,
                "last_error": "broker unavailable",
            },
            {"published_at": CREATED_AT + timedelta(seconds=1)},
        )

        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, "attempt_count"):
                OutboxMessage(**make_message_kwargs(**overrides))

    def test_reject_active_claim_or_failure_metadata_after_publication(self) -> None:
        cases = (
            {"claimed_until": CREATED_AT + timedelta(minutes=1)},
            {
                "failure_category": OutboxFailureCategory.PUBLICATION,
                "last_error": "stale error",
            },
        )

        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                OutboxMessage(
                    **make_message_kwargs(
                        attempt_count=1,
                        published_at=CREATED_AT + timedelta(seconds=1),
                        **overrides,
                    )
                )


def make_draft_kwargs(**overrides: object) -> dict[str, Any]:
    """Build valid outbox-draft arguments with optional field overrides."""
    kwargs: dict[str, Any] = {
        "event_id": EVENT_ID,
        "event_version": 1,
        "event_type": "PackageCreated",
        "occurred_at": OCCURRED_AT,
        "recorded_at": RECORDED_AT,
        "envelope_id": ENVELOPE_ID,
        "correlation_id": CORRELATION_ID,
        "causation_id": CAUSATION_ID,
        "source": EventSource.HTTP,
        "actor_user_id": 7,
        "actor_username": "alice",
        "event_payload_json": {"package_id": 42},
    }
    kwargs.update(overrides)
    return kwargs


def make_message_kwargs(**overrides: object) -> dict[str, Any]:
    """Build valid immediately available message arguments with overrides."""
    kwargs = make_draft_kwargs(
        outbox_id=1,
        created_at=CREATED_AT,
        available_at=CREATED_AT,
        attempt_count=0,
        claimed_until=None,
        published_at=None,
        failure_category=None,
        last_error=None,
    )
    kwargs.update(overrides)
    return kwargs
