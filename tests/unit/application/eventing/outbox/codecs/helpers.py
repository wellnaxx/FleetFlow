"""Shared test mechanics, independent of any concrete codec's wire contract.

Family tests own their expected payloads, identities, and event-specific cases.
These helpers supply stable metadata and repeated assertions without deriving
expectations from the encoder under test or hiding tests behind inheritance.
"""

import json
import unittest
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadDecoder
from src.shared.event import Event
from src.shared.json_types import JSONObject

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)

_INVALID_METADATA_CASES: tuple[tuple[str, object, type[Exception]], ...] = (
    ("event_id", None, TypeError),
    ("event_id", str(EVENT_ID), TypeError),
    ("occurred_at", None, TypeError),
    ("occurred_at", "2030-01-02", TypeError),
    ("recorded_at", None, TypeError),
    ("recorded_at", "2030-01-02", TypeError),
    ("occurred_at", OCCURRED_AT.replace(tzinfo=UTC), ValueError),
    ("recorded_at", RECORDED_AT.replace(tzinfo=None), ValueError),
    ("recorded_at", RECORDED_AT.astimezone(timezone(timedelta(hours=2))), ValueError),
)


def decode_payload[E: Event](codec: EventPayloadDecoder[E], payload: JSONObject) -> E:
    """Decode with fixed metadata while retaining the concrete event return type.

    Payloads are passed through unchanged, allowing callers to check mutation
    behavior themselves. Codec errors propagate to the calling test.
    """
    return codec.decode(payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT)


def json_round_trip(payload: JSONObject) -> JSONObject:
    """Round-trip a payload through real JSON, rejecting NaN and infinity.

    This is also a deep copy of JSON containers. Serialization errors propagate
    rather than being hidden by the helper.
    """
    return cast(JSONObject, json.loads(json.dumps(payload, allow_nan=False)))


def assert_invalid_metadata[E: Event](
    test: unittest.TestCase, codec: EventPayloadDecoder[E], payload: JSONObject
) -> None:
    """Check the common metadata rejection matrix against an otherwise valid payload.

    Each case names its field and value in a subtest and verifies the exception
    type and field-specific message. Fresh payload copies isolate attempts and
    protect the caller's fixture, including nested lists and objects.
    """
    for field, value, error in _INVALID_METADATA_CASES:
        with test.subTest(field=field, value=value):
            metadata: dict[str, object] = {
                "event_id": EVENT_ID,
                "occurred_at": OCCURRED_AT,
                "recorded_at": RECORDED_AT,
            }
            metadata[field] = value
            with test.assertRaisesRegex(error, field):
                codec.decode(
                    deepcopy(payload),
                    event_id=cast(UUID, metadata["event_id"]),
                    occurred_at=cast(datetime, metadata["occurred_at"]),
                    recorded_at=cast(datetime, metadata["recorded_at"]),
                )


def assert_required_keys(
    test: unittest.TestCase, decode: Callable[[JSONObject], object], payload: JSONObject
) -> None:
    """Require every key in a test-owned payload, including keys with null values.

    Remove one field at a time from a fresh deep copy, then check an empty object.
    The caller supplies the expected wire shape explicitly; it is never inferred
    from encoding or a production key constant. Failures name the missing field.
    """
    for field in payload:
        with test.subTest(field=field):
            missing = deepcopy(payload)
            del missing[field]
            with test.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                decode(missing)
    with test.assertRaisesRegex(ValueError, "Missing fields"):
        decode({})
