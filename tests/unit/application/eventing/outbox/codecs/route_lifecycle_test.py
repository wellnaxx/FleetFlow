"""Route creation, scheduling, execution, and removal outbox payload contract tests."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from itertools import product
from typing import cast
from uuid import UUID

from src.application.eventing.outbox.codecs.route_lifecycle import (
    RouteCompletedEventPayloadCodec,
    RouteCreatedEventPayloadCodec,
    RouteRemovedEventPayloadCodec,
    RouteScheduledEventPayloadCodec,
    RouteStartedEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.domain.enums.route_status import RouteStatus
from src.domain.events.route_events import (
    RouteCompleted,
    RouteCreated,
    RouteRemoved,
    RouteScheduled,
    RouteStarted,
)
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")


OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)


RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)


DEPARTURE = datetime(2030, 1, 3, 6, 30, 45, 123456)


COMPLETION = datetime(2030, 1, 4, 18, 45, 30, 654321)


class RouteRemovedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = RouteRemovedEventPayloadCodec()
        self.payload: JSONObject = {
            "route_id": 19,
            "previous_status": RouteStatus.SCHEDULED.value,
            "previous_locations": ["SYD", "BNE", "MEL"],
            "previous_departure_time": DEPARTURE.isoformat(),
            "previous_expected_completion_time": COMPLETION.isoformat(),
            "detached_package_ids": [12, 7],
            "released_truck_id": 1001,
        }
        self.timestamp_fields = ("previous_departure_time", "previous_expected_completion_time")

    def decode(self, payload: JSONObject) -> RouteRemoved:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_all_statuses_and_nullable_combinations(self) -> None:
        for status, departure, completion, truck_id in product(
            RouteStatus, (None, DEPARTURE), (None, COMPLETION), (None, 1001)
        ):
            with self.subTest(status=status, departure=departure, completion=completion, truck=truck_id):
                event = RouteRemoved(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    route_id=19,
                    previous_status=status,
                    previous_locations=(LocationCode("SYD"), LocationCode("BNE"), LocationCode("MEL")),
                    previous_departure_time=departure,
                    previous_expected_completion_time=completion,
                    detached_package_ids=(12, 7),
                    released_truck_id=truck_id,
                )
                expected = dict(self.payload)
                expected.update(
                    previous_status=status.value,
                    previous_departure_time=departure.isoformat() if departure is not None else None,
                    previous_expected_completion_time=(
                        completion.isoformat() if completion is not None else None
                    ),
                    released_truck_id=truck_id,
                )
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                self.assertIs(type(encoded["route_id"]), int)
                self.assertIs(type(encoded["released_truck_id"]), type(truck_id))
                self.assertIs(type(encoded["previous_status"]), str)
                for field, item_type in (("previous_locations", str), ("detached_package_ids", int)):
                    self.assertIs(type(encoded[field]), list)
                    for item in cast(list[JSONValue], encoded[field]):
                        self.assertIs(type(item), item_type)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), RouteRemoved)
                self.assertEqual(restored, event)
                self.assertIs(restored.previous_status, status)
                self.assertIs(type(restored.previous_locations), tuple)
                self.assertIs(type(restored.detached_package_ids), tuple)
                for location in restored.previous_locations:
                    self.assertIsInstance(location, LocationCode)

    def test_requires_every_key_including_nullable_fields(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_misspelled_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "detached_pacakge_ids", "event_id", "event_version", "occurred_at", "recorded_at",
            "envelope_id",
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_validates_route_and_optional_truck_ids_without_coercion(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (True, False, 1.0, "19", "", [], {})
        for field in ("route_id", "released_truck_id"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in (0, -1, -(2**63)):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})
            for value in (1, 1000, 1001, 1040, 1041, 2**63):
                with self.subTest(field=field, value=value):
                    self.assertEqual(getattr(self.decode({**self.payload, field: value}), field), value)
        with self.assertRaisesRegex(TypeError, "route_id"):
            self.decode({**self.payload, "route_id": None})

    def test_requires_list_containers(self) -> None:
        values: tuple[object, ...] = (None, True, 1, 1.5, "SYD", {}, (1, 2), {1, 2})
        for field in ("previous_locations", "detached_package_ids"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_validates_each_location_with_correct_index(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for index in range(3):
            for value in values:
                locations: list[JSONValue] = ["SYD", "BNE", "MEL"]
                locations[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaisesRegex(TypeError, rf"previous_locations\[{index}\]"),
                ):
                    self.decode({**self.payload, "previous_locations": locations})
            for value in ("", " \t\n"):
                locations = ["SYD", "BNE", "MEL"]
                locations[index] = value
                with self.subTest(index=index, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, "previous_locations": locations})

    def test_normalizes_locations_without_sorting_or_deduplicating(self) -> None:
        event = self.decode({**self.payload, "previous_locations": [" syd ", "mel", "SYD"]})
        self.assertEqual(
            event.previous_locations, (LocationCode("SYD"), LocationCode("MEL"), LocationCode("SYD"))
        )
        self.assertEqual(self.codec.encode(event)["previous_locations"], ["SYD", "MEL", "SYD"])

    def test_validates_each_detached_package_id_with_correct_index(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1.0, "7", [], {})
        for index in range(3):
            for value in values:
                ids: list[JSONValue] = [12, 7, 3]
                ids[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaisesRegex(TypeError, rf"detached_package_ids\[{index}\]"),
                ):
                    self.decode({**self.payload, "detached_package_ids": ids})
            for value in (0, -1, -(2**63)):
                ids = [12, 7, 3]
                ids[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaisesRegex(ValueError, rf"detached_package_ids\[{index}\]"),
                ):
                    self.decode({**self.payload, "detached_package_ids": ids})

    def test_preserves_empty_lists_and_package_id_order(self) -> None:
        cases: tuple[list[JSONValue], ...] = ([], [1], [12, 7, 12, 2**63])
        for ids in cases:
            with self.subTest(ids=ids):
                event = self.decode({**self.payload, "detached_package_ids": ids})
                self.assertEqual(event.detached_package_ids, tuple(ids))
                self.assertEqual(self.codec.encode(event)["detached_package_ids"], ids)
        event = self.decode({**self.payload, "previous_locations": [], "detached_package_ids": []})
        self.assertEqual(event.previous_locations, ())
        self.assertEqual(event.detached_package_ids, ())

    def test_rejects_unknown_statuses_and_wrong_types(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "previous_status"):
                self.decode({**self.payload, "previous_status": value})
        for value in ("", "unknown", "scheduled", " SCHEDULED "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decode({**self.payload, "previous_status": value})

    def test_rejects_non_string_schedule_timestamps(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, DEPARTURE)
        for field in self.timestamp_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_schedule_timestamps(self) -> None:
        for field in self.timestamp_fields:
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_timestamp_text_preserves_parse_error_as_cause(self) -> None:
        for field in self.timestamp_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_payload_and_lists_are_not_mutated_or_retained(self) -> None:
        original = cast(JSONObject, json.loads(json.dumps(self.payload)))
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        cast(list[JSONValue], self.payload["previous_locations"])[0] = "PER"
        cast(list[JSONValue], self.payload["detached_package_ids"]).append(999)
        self.assertEqual(event.previous_locations[0], LocationCode("SYD"))
        self.assertEqual(event.detached_package_ids, (12, 7))
        encoded = self.codec.encode(event)
        cast(list[JSONValue], encoded["previous_locations"]).append("PER")
        cast(list[JSONValue], encoded["detached_package_ids"]).clear()
        encoded["released_truck_id"] = None
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_other_route_events(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        registry.register(RouteCompleted, RouteCompletedEventPayloadCodec())
        registry.register(RouteRemoved, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("route_removed", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, RouteRemoved)
        self.assertEqual(adapter.event_version, RouteRemoved.event_version)
        for name in ("route_created", "route_completed"):
            self.assertIsNot(adapter, registry.for_identity(name, 2))
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("route_removed", version)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
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
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                metadata: dict[str, object] = {
                    "event_id": EVENT_ID,
                    "occurred_at": OCCURRED_AT,
                    "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )


class RouteCompletedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = RouteCompletedEventPayloadCodec()
        self.payload: JSONObject = {
            "route_id": 19,
            "previous_status": RouteStatus.IN_PROGRESS.value,
            "new_status": RouteStatus.COMPLETED.value,
            "departure_time": DEPARTURE.isoformat(),
            "expected_completion_time": COMPLETION.isoformat(),
        }
        self.timestamp_fields = ("departure_time", "expected_completion_time")

    def decode(self, payload: JSONObject) -> RouteCompleted:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_completion_from_scheduled_and_in_progress(self) -> None:
        for previous_status in (RouteStatus.SCHEDULED, RouteStatus.IN_PROGRESS):
            with self.subTest(previous_status=previous_status):
                event = RouteCompleted(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    route_id=19,
                    previous_status=previous_status,
                    new_status=RouteStatus.COMPLETED,
                    departure_time=DEPARTURE,
                    expected_completion_time=COMPLETION,
                )
                expected = {**self.payload, "previous_status": previous_status.value}
                encoded = self.codec.encode(event)
                self.assertEqual(encoded, expected)
                self.assertIs(type(encoded["route_id"]), int)
                for field in ("previous_status", "new_status", *self.timestamp_fields):
                    self.assertIs(type(encoded[field]), str)
                restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                self.assertIs(type(restored), RouteCompleted)
                self.assertEqual(restored, event)
                self.assertIs(restored.previous_status, previous_status)
                self.assertIs(restored.new_status, RouteStatus.COMPLETED)

    def test_preserves_all_status_values_without_reapplying_transition_rules(self) -> None:
        for previous_status, new_status in product(RouteStatus, repeat=2):
            with self.subTest(previous_status=previous_status, new_status=new_status):
                payload = {
                    **self.payload, "previous_status": previous_status.value, "new_status": new_status.value
                }
                event = self.decode(payload)
                self.assertIs(event.previous_status, previous_status)
                self.assertIs(event.new_status, new_status)
                self.assertEqual(self.codec.encode(event), payload)

    def test_requires_every_key(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_and_metadata_keys(self) -> None:
        for field in ("unknown", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_validates_route_id_without_coercion(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, False, 1.0, "19", "", [], {})
        for value in wrong_types:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (1, 2**63):
            with self.subTest(value=value):
                self.assertEqual(self.decode({**self.payload, "route_id": value}).route_id, value)

    def test_rejects_unknown_statuses_and_wrong_types_for_both_fields(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_status", "new_status"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("unknown", "", "completed", " COMPLETED ", "In Progress"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, field: value})

    def test_rejects_null_and_non_string_schedule_timestamps(self) -> None:
        values: tuple[object, ...] = (None, True, False, 1, 1.5, [], {}, DEPARTURE)
        for field in self.timestamp_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_schedule_timestamps(self) -> None:
        for field in self.timestamp_fields:
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_timestamp_text_preserves_parse_error_as_cause(self) -> None:
        for field in self.timestamp_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_preserves_expected_completion_when_event_is_recorded_later(self) -> None:
        occurred_at = COMPLETION + timedelta(hours=3)
        recorded_at = occurred_at.replace(tzinfo=UTC) + timedelta(minutes=5)
        event = self.codec.decode(
            self.payload, event_id=EVENT_ID, occurred_at=occurred_at, recorded_at=recorded_at
        )
        self.assertEqual(event.expected_completion_time, COMPLETION)
        self.assertEqual(event.departure_time, DEPARTURE)
        self.assertEqual(event.occurred_at, occurred_at)
        self.assertEqual(event.recorded_at, recorded_at)
        self.assertEqual(self.codec.encode(event), self.payload)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["expected_completion_time"] = None
        self.assertEqual(event.expected_completion_time, COMPLETION)
        encoded = self.codec.encode(event)
        encoded["route_id"] = 999
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_other_route_events(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        registry.register(RouteScheduled, RouteScheduledEventPayloadCodec())
        registry.register(RouteStarted, RouteStartedEventPayloadCodec())
        registry.register(RouteCompleted, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("route_completed", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, RouteCompleted)
        self.assertEqual(adapter.event_version, RouteCompleted.event_version)
        for name in ("route_created", "route_scheduled", "route_started"):
            self.assertIsNot(adapter, registry.for_identity(name, 2))
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("route_completed", version)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
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
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                metadata: dict[str, object] = {
                    "event_id": EVENT_ID,
                    "occurred_at": OCCURRED_AT,
                    "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )


class RouteStartedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = RouteStartedEventPayloadCodec()
        self.payload: JSONObject = {
            "route_id": 19,
            "previous_status": RouteStatus.SCHEDULED.value,
            "new_status": RouteStatus.IN_PROGRESS.value,
        }

    def decode(self, payload: JSONObject) -> RouteStarted:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_and_json_round_trip(self) -> None:
        event = RouteStarted(
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
            route_id=19,
            previous_status=RouteStatus.SCHEDULED,
            new_status=RouteStatus.IN_PROGRESS,
        )
        encoded = self.codec.encode(event)
        self.assertEqual(encoded, self.payload)
        self.assertIs(type(encoded["route_id"]), int)
        self.assertIs(type(encoded["previous_status"]), str)
        self.assertIs(type(encoded["new_status"]), str)
        restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
        self.assertIs(type(restored), RouteStarted)
        self.assertEqual(restored, event)
        self.assertIs(restored.previous_status, RouteStatus.SCHEDULED)
        self.assertIs(restored.new_status, RouteStatus.IN_PROGRESS)

    def test_preserves_all_status_values_without_reapplying_transition_rules(self) -> None:
        for previous_status, new_status in product(RouteStatus, repeat=2):
            with self.subTest(previous_status=previous_status, new_status=new_status):
                payload = {
                    **self.payload, "previous_status": previous_status.value, "new_status": new_status.value
                }
                event = self.decode(payload)
                self.assertIs(event.previous_status, previous_status)
                self.assertIs(event.new_status, new_status)
                self.assertEqual(self.codec.encode(event), payload)

    def test_requires_every_key(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_schedule_and_metadata_keys(self) -> None:
        for field in (
            "unknown", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id",
            "departure_time", "start_time",
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_validates_route_id_without_coercion_and_reports_correct_field(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, False, 1.0, "19", "", [], {})
        for value in wrong_types:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (1, 2**63):
            with self.subTest(value=value):
                self.assertEqual(self.decode({**self.payload, "route_id": value}).route_id, value)

    def test_rejects_unknown_statuses_and_wrong_types_for_both_fields(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_status", "new_status"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("unknown", "", "scheduled", " SCHEDULED ", "In Progress"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, field: value})

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["new_status"] = RouteStatus.COMPLETED.value
        self.assertIs(event.new_status, RouteStatus.IN_PROGRESS)
        encoded = self.codec.encode(event)
        encoded["route_id"] = 999
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_other_route_events(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        registry.register(RouteScheduled, RouteScheduledEventPayloadCodec())
        registry.register(RouteStarted, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("route_started", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, RouteStarted)
        self.assertEqual(adapter.event_version, RouteStarted.event_version)
        for name in ("route_created", "route_scheduled"):
            self.assertIsNot(adapter, registry.for_identity(name, 2))
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("route_started", version)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
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
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                metadata: dict[str, object] = {
                    "event_id": EVENT_ID,
                    "occurred_at": OCCURRED_AT,
                    "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )


class RouteScheduledCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = RouteScheduledEventPayloadCodec()
        self.previous_departure = DEPARTURE - timedelta(days=1)
        self.previous_completion = COMPLETION - timedelta(days=1)
        self.payload: JSONObject = {
            "route_id": 19,
            "previous_status": RouteStatus.PLANNED.value,
            "new_status": RouteStatus.SCHEDULED.value,
            "previous_departure_time": self.previous_departure.isoformat(),
            "new_departure_time": DEPARTURE.isoformat(),
            "previous_expected_completion_time": self.previous_completion.isoformat(),
            "new_expected_completion_time": COMPLETION.isoformat(),
        }
        self.timestamp_fields = (
            "previous_departure_time", "new_departure_time",
            "previous_expected_completion_time", "new_expected_completion_time",
        )

    def decode(self, payload: JSONObject) -> RouteScheduled:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_nullable_previous_timestamps(self) -> None:
        for previous_departure in (None, self.previous_departure):
            for previous_completion in (None, self.previous_completion):
                with self.subTest(departure=previous_departure, completion=previous_completion):
                    event = RouteScheduled(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        route_id=19,
                        previous_status=RouteStatus.PLANNED,
                        new_status=RouteStatus.SCHEDULED,
                        previous_departure_time=previous_departure,
                        new_departure_time=DEPARTURE,
                        previous_expected_completion_time=previous_completion,
                        new_expected_completion_time=COMPLETION,
                    )
                    expected = dict(self.payload)
                    expected.update(
                        previous_departure_time=(
                            previous_departure.isoformat() if previous_departure is not None else None
                        ),
                        previous_expected_completion_time=(
                            previous_completion.isoformat() if previous_completion is not None else None
                        ),
                    )
                    encoded = self.codec.encode(event)
                    self.assertEqual(encoded, expected)
                    self.assertIs(type(encoded["route_id"]), int)
                    for field in ("previous_status", "new_status", *self.timestamp_fields):
                        if encoded[field] is not None:
                            self.assertIs(type(encoded[field]), str)
                    restored = self.decode(cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False))))
                    self.assertIs(type(restored), RouteScheduled)
                    self.assertEqual(restored, event)
                    self.assertIs(restored.previous_status, RouteStatus.PLANNED)
                    self.assertIs(restored.new_status, RouteStatus.SCHEDULED)

    def test_preserves_all_status_values_without_reapplying_transition_rules(self) -> None:
        for previous_status in RouteStatus:
            for new_status in RouteStatus:
                with self.subTest(previous_status=previous_status, new_status=new_status):
                    payload = {
                        **self.payload,
                        "previous_status": previous_status.value,
                        "new_status": new_status.value,
                    }
                    event = self.decode(payload)
                    self.assertIs(event.previous_status, previous_status)
                    self.assertIs(event.new_status, new_status)
                    self.assertEqual(self.codec.encode(event), payload)

    def test_requires_every_key_including_nullable_timestamps(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_and_metadata_keys(self) -> None:
        for field in ("unknown", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_validates_route_id_without_coercion(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, False, 1.0, "19", "", [], {})
        for value in wrong_types:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (1, 2**63):
            with self.subTest(value=value):
                self.assertEqual(self.decode({**self.payload, "route_id": value}).route_id, value)

    def test_rejects_unknown_statuses_and_wrong_types_for_both_fields(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for field in ("previous_status", "new_status"):
            for value in wrong_types:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: value})
            for value in ("unknown", "", "scheduled", " SCHEDULED "):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decode({**self.payload, field: value})

    def test_rejects_null_new_timestamps(self) -> None:
        for field in ("new_departure_time", "new_expected_completion_time"):
            with self.subTest(field=field), self.assertRaisesRegex(TypeError, field):
                self.decode({**self.payload, field: None})

    def test_rejects_non_string_timestamps_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, DEPARTURE)
        for field in self.timestamp_fields:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_timestamps(self) -> None:
        for field in self.timestamp_fields:
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_timestamp_text_preserves_parse_error_as_cause(self) -> None:
        for field in self.timestamp_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_payload_and_event_remain_independent(self) -> None:
        original = dict(self.payload)
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        self.payload["new_departure_time"] = None
        self.assertEqual(event.new_departure_time, DEPARTURE)
        encoded = self.codec.encode(event)
        encoded["route_id"] = 999
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_without_conflicting_with_created(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
        registry.register(RouteScheduled, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("route_scheduled", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, RouteScheduled)
        self.assertEqual(adapter.event_version, RouteScheduled.event_version)
        self.assertIsNot(adapter, registry.for_identity("route_created", 2))
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("route_scheduled", version)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
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
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                metadata: dict[str, object] = {
                    "event_id": EVENT_ID,
                    "occurred_at": OCCURRED_AT,
                    "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )


class RouteCreatedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = RouteCreatedEventPayloadCodec()
        self.payload: JSONObject = {
            "route_id": 19,
            "locations": ["SYD", "BNE", "MEL"],
            "departure_time": DEPARTURE.isoformat(),
            "initial_status": RouteStatus.SCHEDULED.value,
            "expected_completion_time": COMPLETION.isoformat(),
        }

    def decode(self, payload: JSONObject) -> RouteCreated:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_exact_wire_contract_round_trips_all_statuses_and_nullable_timestamps(self) -> None:
        for status in RouteStatus:
            for departure in (None, DEPARTURE):
                for completion in (None, COMPLETION):
                    with self.subTest(status=status, departure=departure, completion=completion):
                        event = RouteCreated(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            route_id=19,
                            locations=(LocationCode("SYD"), LocationCode("BNE"), LocationCode("MEL")),
                            departure_time=departure,
                            initial_status=status,
                            expected_completion_time=completion,
                        )
                        expected = dict(self.payload)
                        expected.update(
                            initial_status=status.value,
                            departure_time=departure.isoformat() if departure is not None else None,
                            expected_completion_time=completion.isoformat() if completion is not None else None,
                        )
                        encoded = self.codec.encode(event)
                        self.assertEqual(encoded, expected)
                        self.assertIs(type(encoded["route_id"]), int)
                        self.assertIs(type(encoded["initial_status"]), str)
                        self.assertIs(type(encoded["locations"]), list)
                        for location in cast(list[JSONValue], encoded["locations"]):
                            self.assertIs(type(location), str)
                        restored = self.decode(
                            cast(JSONObject, json.loads(json.dumps(encoded, allow_nan=False)))
                        )
                        self.assertIs(type(restored), RouteCreated)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.initial_status, status)
                        self.assertIs(type(restored.locations), tuple)
                        for location in restored.locations:
                            self.assertIsInstance(location, LocationCode)

    def test_requires_every_key_including_nullable_timestamps(self) -> None:
        for field in self.payload:
            with self.subTest(field=field):
                payload = dict(self.payload)
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_rejects_unknown_and_metadata_keys(self) -> None:
        for field in ("unknown", "event_id", "event_version", "occurred_at", "recorded_at", "envelope_id"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                self.decode({**self.payload, field: "unexpected"})

    def test_validates_route_id_without_coercion(self) -> None:
        wrong_types: tuple[JSONValue, ...] = (None, True, False, 1.0, "19", "", [], {})
        for value in wrong_types:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "route_id"):
                self.decode({**self.payload, "route_id": value})
        for value in (1, 2**63):
            with self.subTest(value=value):
                self.assertEqual(self.decode({**self.payload, "route_id": value}).route_id, value)

    def test_requires_locations_to_be_a_list(self) -> None:
        values: tuple[object, ...] = (None, True, 1, 1.5, "SYD", {}, ("SYD", "MEL"), {"SYD", "MEL"})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "locations"):
                self.decode({**self.payload, "locations": cast(JSONValue, value)})

    def test_rejects_non_string_locations_with_correct_index(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, False, 1, 1.5, [], {})
        for index in range(3):
            for value in values:
                locations: list[JSONValue] = ["SYD", "BNE", "MEL"]
                locations[index] = value
                with (
                    self.subTest(index=index, value=value),
                    self.assertRaisesRegex(TypeError, rf"locations\[{index}\]: expected str"),
                ):
                    self.decode({**self.payload, "locations": locations})

    def test_rejects_blank_locations(self) -> None:
        for index in range(3):
            for value in ("", " \t\n"):
                locations: list[JSONValue] = ["SYD", "BNE", "MEL"]
                locations[index] = value
                with self.subTest(index=index, value=value), self.assertRaises(DomainValidationError):
                    self.decode({**self.payload, "locations": locations})

    def test_normalizes_locations_without_sorting_or_deduplicating(self) -> None:
        event = self.decode({**self.payload, "locations": [" syd ", "mel", "SYD"]})
        self.assertEqual(event.locations, (LocationCode("SYD"), LocationCode("MEL"), LocationCode("SYD")))
        self.assertEqual(self.codec.encode(event)["locations"], ["SYD", "MEL", "SYD"])

    def test_does_not_reapply_route_path_or_map_policies(self) -> None:
        cases: tuple[list[JSONValue], ...] = ([], ["SYD"], ["SYD", "SYD"], ["CUSTOM_A", "CUSTOM_B"])
        for locations in cases:
            with self.subTest(locations=locations):
                event = self.decode({**self.payload, "locations": locations})
                self.assertEqual(self.codec.encode(event)["locations"], locations)

    def test_rejects_unknown_status_values_and_wrong_types(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "initial_status"):
                self.decode({**self.payload, "initial_status": value})
        for value in ("unknown", "", "scheduled", " SCHEDULED "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decode({**self.payload, "initial_status": value})

    def test_rejects_non_string_timestamps_including_datetime_objects(self) -> None:
        values: tuple[object, ...] = (True, False, 1, 1.5, [], {}, DEPARTURE)
        for field in ("departure_time", "expected_completion_time"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(TypeError, field):
                    self.decode({**self.payload, field: cast(JSONValue, value)})

    def test_rejects_invalid_or_timezone_aware_timestamps(self) -> None:
        for field in ("departure_time", "expected_completion_time"):
            for value in (
                "", " ", "invalid", "2030-02-30T12:00:00", "2030-01-01T25:00:00",
                "2030-01-01T12:00:00Z", "2030-01-01T12:00:00+00:00", "2030-01-01T12:00:00+02:00",
                "2030-01-01T12:00:00-03:00",
            ):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.decode({**self.payload, field: value})

    def test_invalid_timestamp_text_preserves_parse_error_as_cause(self) -> None:
        for field in ("departure_time", "expected_completion_time"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field) as raised:
                    self.decode({**self.payload, field: "invalid"})
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_payload_and_location_list_are_not_mutated_or_retained(self) -> None:
        original = cast(JSONObject, json.loads(json.dumps(self.payload)))
        event = self.decode(self.payload)
        self.assertEqual(self.payload, original)
        cast(list[JSONValue], self.payload["locations"])[0] = "PER"
        self.assertEqual(event.locations[0], LocationCode("SYD"))
        encoded = self.codec.encode(event)
        cast(list[JSONValue], encoded["locations"]).append("PER")
        encoded["route_id"] = 999
        self.assertEqual(self.codec.encode(event), original)

    def test_registry_resolves_version_two_and_round_trips_through_adapter(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(RouteCreated, self.codec)
        event = self.decode(self.payload)
        adapter = registry.for_identity("route_created", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, RouteCreated)
        self.assertEqual(adapter.event_version, RouteCreated.event_version)
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("route_created", version)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
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
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                metadata: dict[str, object] = {
                    "event_id": EVENT_ID,
                    "occurred_at": OCCURRED_AT,
                    "recorded_at": RECORDED_AT,
                }
                metadata[field] = value
                with self.assertRaisesRegex(error, field):
                    self.codec.decode(
                        self.payload,
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )
