"""Own-password changes and administrative password resets outbox payload contract tests."""

import unittest

from src.application.enums.user_password_change_rejection_reasons import UserPasswordChangeRejectionReason
from src.application.enums.user_password_reset_rejection_reasons import UserPasswordResetRejectionReason
from src.application.eventing.outbox.codecs.auth_passwords import (
    UserPasswordChangedEventPayloadCodec,
    UserPasswordChangeRejectedEventPayloadCodec,
    UserPasswordResetEventPayloadCodec,
    UserPasswordResetRejectedEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.auth_events import (
    UserPasswordChanged,
    UserPasswordChangeRejected,
    UserPasswordReset,
    UserPasswordResetRejected,
)
from src.shared.json_types import JSONObject, JSONValue
from tests.unit.application.eventing.outbox.codecs.helpers import (
    EVENT_ID,
    OCCURRED_AT,
    RECORDED_AT,
    assert_invalid_metadata,
    assert_required_keys,
    decode_payload,
    json_round_trip,
)


class UserPasswordResetRejectedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserPasswordResetRejectedEventPayloadCodec()

    def make_payload(self) -> JSONObject:
        return {"user_id": 7, "username": "alice", "reason": "CANNOT_RESET_OWN_PASSWORD"}

    def decode(self, payload: JSONObject) -> UserPasswordResetRejected:
        return decode_payload(self.codec, payload)

    def test_exact_wire_contract_and_json_round_trip_for_every_reason(self) -> None:
        for reason in UserPasswordResetRejectionReason:
            for user_id in (None, 1, 2**63):
                for username in (None, "alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                    with self.subTest(reason=reason, user_id=user_id, username=username):
                        event = UserPasswordResetRejected(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            user_id=user_id,
                            username=username,
                            reason=reason,
                        )
                        encoded = self.codec.encode(event)
                        self.assertEqual(
                            encoded, {"user_id": user_id, "username": username, "reason": reason.value}
                        )
                        restored = self.decode(json_round_trip(encoded))
                        self.assertIs(type(restored), UserPasswordResetRejected)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.reason, reason)

    def test_requires_every_key_even_when_identity_values_are_null(self) -> None:
        assert_required_keys(
            self, self.decode, {"user_id": None, "username": None, "reason": "INVALID_USERNAME"}
        )

    def test_rejects_extra_credentials_actor_and_event_metadata(self) -> None:
        for field in ("new_password", "password_hash", "actor_user_id", "event_id"):
            with self.subTest(field=field):
                payload = self.make_payload()
                payload[field] = "unexpected"
                with self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                    self.decode(payload)

    def test_rejects_non_positive_user_ids(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value):
                payload = self.make_payload()
                payload["user_id"] = value
                with self.assertRaisesRegex(ValueError, "user_id must be a positive integer"):
                    self.decode(payload)

    def test_rejects_wrong_field_types_without_coercion(self) -> None:
        invalid_by_field: dict[str, tuple[JSONValue, ...]] = {
            "user_id": (True, False, 1.0, "7", "", [], {}),
            "username": (True, False, 7, 1.5, [], {}),
            "reason": (None, True, False, 7, 1.5, [], {}),
        }
        for field, values in invalid_by_field.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    payload = self.make_payload()
                    payload[field] = value
                    with self.assertRaisesRegex(TypeError, field):
                        self.decode(payload)

    def test_rejects_unknown_and_password_change_only_reasons(self) -> None:
        for reason in (
            "", "UNKNOWN", "invalid_username", " INVALID_USERNAME ", "1",
            "CURRENT_PASSWORD_INCORRECT", "SAME_AS_CURRENT_PASSWORD", "INVALID_PASSWORD_HASH",
        ):
            with self.subTest(reason=reason):
                payload = self.make_payload()
                payload["reason"] = reason
                with self.assertRaises(ValueError):
                    self.decode(payload)

    def test_payload_and_event_are_independent(self) -> None:
        payload = self.make_payload()
        event = self.decode(payload)
        self.assertEqual(payload, self.make_payload())
        payload["username"] = "changed"
        self.assertEqual(event.username, "alice")
        encoded = self.codec.encode(event)
        encoded["reason"] = "USER_NOT_FOUND"
        self.assertEqual(self.codec.encode(event), self.make_payload())

    def test_registry_distinguishes_reset_rejection_from_change_rejection(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserPasswordResetRejected, self.codec)
        registry.register(UserPasswordChangeRejected, UserPasswordChangeRejectedEventPayloadCodec())
        event = self.decode(self.make_payload())
        adapter = registry.for_identity("user_password_reset_rejected", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserPasswordResetRejected)
        self.assertEqual(adapter.event_version, 1)
        self.assertIsNot(adapter, registry.for_identity("user_password_change_rejected", 1))
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("user_password_reset_rejected", 2)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.make_payload())


class UserPasswordResetCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserPasswordResetEventPayloadCodec()

    def make_payload(self) -> JSONObject:
        return {"user_id": 7, "username": "alice"}

    def decode(self, payload: JSONObject) -> UserPasswordReset:
        return decode_payload(self.codec, payload)

    def test_exact_wire_contract_and_json_round_trip_preserve_account_and_metadata(self) -> None:
        for user_id in (1, 7, 2**63):
            for username in ("alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                with self.subTest(user_id=user_id, username=username):
                    event = UserPasswordReset(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        user_id=user_id,
                        username=username,
                    )
                    encoded = self.codec.encode(event)
                    self.assertEqual(encoded, {"user_id": user_id, "username": username})
                    self.assertIs(type(encoded["user_id"]), int)
                    payload = json_round_trip(encoded)
                    restored = self.decode(payload)
                    self.assertIs(type(restored), UserPasswordReset)
                    self.assertEqual(restored, event)

    def test_requires_every_key_and_rejects_empty_payload(self) -> None:
        assert_required_keys(self, self.decode, self.make_payload())

    def test_rejects_extra_fields_including_credentials_actor_and_metadata(self) -> None:
        for field in ("new_password", "password_hash", "actor_user_id", "event_id", "reason"):
            with self.subTest(field=field):
                payload = self.make_payload()
                payload[field] = "unexpected"
                with self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                    self.decode(payload)

    def test_rejects_non_positive_user_ids(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value):
                payload = self.make_payload()
                payload["user_id"] = value
                with self.assertRaisesRegex(ValueError, "user_id must be a positive integer"):
                    self.decode(payload)

    def test_rejects_wrong_field_types_without_coercion(self) -> None:
        invalid_by_field: dict[str, tuple[JSONValue, ...]] = {
            "user_id": (None, True, False, 1.0, "7", "", [], {}),
            "username": (None, True, False, 7, 1.5, [], {}),
        }
        for field, values in invalid_by_field.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    payload = self.make_payload()
                    payload[field] = value
                    with self.assertRaisesRegex(TypeError, field):
                        self.decode(payload)

    def test_payload_and_event_remain_independent(self) -> None:
        payload = self.make_payload()
        event = self.decode(payload)
        self.assertEqual(payload, self.make_payload())
        payload["username"] = "changed"
        self.assertEqual(event.username, "alice")
        encoded = self.codec.encode(event)
        encoded["user_id"] = 999
        self.assertEqual(self.codec.encode(event), self.make_payload())

    def test_registry_distinguishes_reset_from_change_and_rejects_unknown_version(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserPasswordReset, self.codec)
        registry.register(UserPasswordChanged, UserPasswordChangedEventPayloadCodec())
        event = self.decode(self.make_payload())
        adapter = registry.for_identity("user_password_reset", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserPasswordReset)
        self.assertEqual(adapter.event_version, 1)
        self.assertIsNot(adapter, registry.for_identity("user_password_changed", 1))
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("user_password_reset", 2)

    def test_event_constructor_validates_supplied_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.make_payload())


class UserPasswordChangeRejectedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserPasswordChangeRejectedEventPayloadCodec()

    def make_payload(self) -> JSONObject:
        return {"user_id": 7, "username": "alice", "reason": "CURRENT_PASSWORD_INCORRECT"}

    def decode(self, payload: JSONObject) -> UserPasswordChangeRejected:
        return decode_payload(self.codec, payload)

    def test_exact_wire_contract_and_json_round_trip_for_every_reason(self) -> None:
        for reason in UserPasswordChangeRejectionReason:
            for user_id in (None, 1, 2**63):
                for username in (None, "alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                    with self.subTest(reason=reason, user_id=user_id, username=username):
                        event = UserPasswordChangeRejected(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            user_id=user_id,
                            username=username,
                            reason=reason,
                        )
                        encoded = self.codec.encode(event)
                        self.assertEqual(
                            encoded, {"user_id": user_id, "username": username, "reason": reason.value}
                        )
                        payload = json_round_trip(encoded)
                        restored = self.decode(payload)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.reason, reason)

    def test_requires_all_keys_even_when_identity_is_null(self) -> None:
        assert_required_keys(
            self, self.decode, {"user_id": None, "username": None, "reason": "INVALID_USERNAME"}
        )

    def test_rejects_extra_fields_including_credentials_and_metadata(self) -> None:
        for field in ("current_password", "new_password", "password_hash", "event_id"):
            with self.subTest(field=field):
                payload = self.make_payload()
                payload[field] = "unexpected"
                with self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                    self.decode(payload)

    def test_rejects_non_positive_ids(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value):
                payload = self.make_payload()
                payload["user_id"] = value
                with self.assertRaisesRegex(ValueError, "user_id must be a positive integer"):
                    self.decode(payload)

    def test_rejects_wrong_field_types_without_coercion(self) -> None:
        invalid_by_field: dict[str, tuple[JSONValue, ...]] = {
            "user_id": (True, False, 1.0, "7", "", [], {}),
            "username": (True, False, 7, 1.5, [], {}),
            "reason": (None, True, False, 7, 1.5, [], {}),
        }
        for field, values in invalid_by_field.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    payload = self.make_payload()
                    payload[field] = value
                    with self.assertRaisesRegex(TypeError, field):
                        self.decode(payload)

    def test_unknown_reason_raises_value_error(self) -> None:
        for reason in ("", "UNKNOWN", "invalid_username", " INVALID_USERNAME ", "1"):
            with self.subTest(reason=reason):
                payload = self.make_payload()
                payload["reason"] = reason
                with self.assertRaises(ValueError):
                    self.decode(payload)

    def test_payload_and_event_remain_independent(self) -> None:
        payload = self.make_payload()
        event = self.decode(payload)
        self.assertEqual(payload, self.make_payload())
        payload["username"] = "changed"
        self.assertEqual(event.username, "alice")
        encoded = self.codec.encode(event)
        encoded["reason"] = "INVALID_USERNAME"
        self.assertEqual(self.codec.encode(event), self.make_payload())

    def test_registry_resolves_exact_version_and_round_trips(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserPasswordChangeRejected, self.codec)
        event = self.decode(self.make_payload())
        adapter = registry.for_identity("user_password_change_rejected", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserPasswordChangeRejected)
        self.assertEqual(adapter.event_version, 1)
        self.assertEqual(
            adapter.decode(
                registry.for_event(event).encode(event),
                event_id=EVENT_ID,
                occurred_at=OCCURRED_AT,
                recorded_at=RECORDED_AT,
            ),
            event,
        )
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("user_password_change_rejected", 2)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.make_payload())


class UserPasswordChangedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserPasswordChangedEventPayloadCodec()

    def make_payload(self) -> JSONObject:
        return {"user_id": 7, "username": "alice"}

    def decode(self, payload: JSONObject) -> UserPasswordChanged:
        return decode_payload(self.codec, payload)

    def test_encodes_exact_identity_fields_without_credentials_or_metadata(self) -> None:
        event = UserPasswordChanged(
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
            user_id=7,
            username="alice",
        )
        self.assertEqual(self.codec.encode(event), self.make_payload())
        self.assertIs(type(self.codec.encode(event)["user_id"]), int)

    def test_json_round_trip_preserves_identity_and_metadata(self) -> None:
        for user_id in (1, 7, 2**63):
            for username in ("alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                with self.subTest(user_id=user_id, username=username):
                    event = UserPasswordChanged(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        user_id=user_id,
                        username=username,
                    )
                    payload = json_round_trip(self.codec.encode(event))
                    self.assertEqual(self.decode(payload), event)

    def test_requires_every_key_and_rejects_empty_payload(self) -> None:
        assert_required_keys(self, self.decode, self.make_payload())

    def test_rejects_extra_fields_including_credentials_and_metadata(self) -> None:
        for field in ("password", "password_hash", "event_id", "reason"):
            with self.subTest(field=field):
                payload = self.make_payload()
                payload[field] = "unexpected"
                with self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                    self.decode(payload)

    def test_rejects_non_positive_user_ids(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value):
                payload = self.make_payload()
                payload["user_id"] = value
                with self.assertRaisesRegex(ValueError, "user_id must be a positive integer"):
                    self.decode(payload)

    def test_rejects_wrong_field_types_without_coercion(self) -> None:
        invalid_by_field: dict[str, tuple[JSONValue, ...]] = {
            "user_id": (None, True, False, 1.0, "7", "", [], {}),
            "username": (None, True, False, 7, 1.5, [], {}),
        }
        for field, values in invalid_by_field.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    payload = self.make_payload()
                    payload[field] = value
                    with self.assertRaisesRegex(TypeError, field):
                        self.decode(payload)

    def test_codec_does_not_mutate_or_retain_input_payload(self) -> None:
        payload = self.make_payload()
        event = self.decode(payload)
        self.assertEqual(payload, self.make_payload())
        payload["username"] = "changed"
        self.assertEqual(event.username, "alice")
        encoded = self.codec.encode(event)
        encoded["user_id"] = 999
        self.assertEqual(self.codec.encode(event), self.make_payload())

    def test_registry_resolves_exact_version_and_preserves_decoded_event(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserPasswordChanged, self.codec)
        event = self.decode(self.make_payload())
        adapter = registry.for_identity("user_password_changed", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserPasswordChanged)
        self.assertEqual(adapter.event_version, 1)
        restored = adapter.decode(
            registry.for_event(event).encode(event),
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
        )
        self.assertEqual(restored, event)
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("user_password_changed", 2)

    def test_event_constructor_validates_supplied_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.make_payload())
