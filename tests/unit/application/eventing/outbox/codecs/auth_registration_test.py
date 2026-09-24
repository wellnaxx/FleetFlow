"""User registration successes and rejections outbox payload contract tests."""

import unittest

from src.application.enums.user_registration_rejection_reasons import UserRegistrationRejectionReason
from src.application.eventing.outbox.codecs.auth_registration import (
    UserRegisteredEventPayloadCodec,
    UserRegistrationRejectedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.auth_sessions import (
    UserAuthenticatedEventPayloadCodec,
    UserLoginRejectedEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.auth_events import (
    UserAuthenticated,
    UserLoginRejected,
    UserRegistered,
    UserRegistrationRejected,
)
from src.domain.enums.auth import Role
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


def make_authenticated_payload() -> JSONObject:
    return {"user_id": 7, "username": "alice", "role": "MANAGER"}


class UserRegistrationRejectedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserRegistrationRejectedEventPayloadCodec()

    def make_payload(self) -> JSONObject:
        return {"username": "alice", "reason": "USERNAME_ALREADY_EXISTS"}

    def decode(self, payload: JSONObject) -> UserRegistrationRejected:
        return decode_payload(self.codec, payload)

    def test_exact_wire_contract_and_json_round_trip_for_every_reason(self) -> None:
        for reason in UserRegistrationRejectionReason:
            for username in (None, "alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                with self.subTest(reason=reason, username=username):
                    event = UserRegistrationRejected(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        username=username,
                        reason=reason,
                    )
                    encoded = self.codec.encode(event)
                    self.assertEqual(encoded, {"username": username, "reason": reason.value})
                    restored = self.decode(json_round_trip(encoded))
                    self.assertIs(type(restored), UserRegistrationRejected)
                    self.assertEqual(restored, event)
                    self.assertIs(restored.reason, reason)

    def test_requires_every_key_including_nullable_username(self) -> None:
        assert_required_keys(self, self.decode, {"username": None, "reason": "INVALID_USERNAME"})

    def test_rejects_extra_account_credentials_and_metadata_fields(self) -> None:
        for field in ("user_id", "role", "password", "password_hash", "actor_user_id", "event_id"):
            with self.subTest(field=field):
                payload = self.make_payload()
                payload[field] = "unexpected"
                with self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                    self.decode(payload)

    def test_rejects_wrong_field_types_without_coercion(self) -> None:
        invalid_by_field: dict[str, tuple[JSONValue, ...]] = {
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

    def test_rejects_unknown_and_other_workflow_reasons(self) -> None:
        for reason in (
            "", "UNKNOWN", "invalid_username", " INVALID_USERNAME ", "1",
            "USER_NOT_FOUND", "CANNOT_RESET_OWN_PASSWORD", "CURRENT_PASSWORD_INCORRECT",
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
        encoded["reason"] = "INVALID_USERNAME"
        self.assertEqual(self.codec.encode(event), self.make_payload())

    def test_registry_distinguishes_rejection_from_success_and_other_rejections(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserRegistrationRejected, self.codec)
        registry.register(UserRegistered, UserRegisteredEventPayloadCodec())
        registry.register(UserLoginRejected, UserLoginRejectedEventPayloadCodec())
        event = self.decode(self.make_payload())
        adapter = registry.for_identity("user_registration_rejected", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserRegistrationRejected)
        self.assertEqual(adapter.event_version, 1)
        self.assertIsNot(adapter, registry.for_identity("user_registered", 1))
        self.assertIsNot(adapter, registry.for_identity("user_login_rejected", 1))
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
            registry.for_identity("user_registration_rejected", 2)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.make_payload())


class UserRegisteredCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserRegisteredEventPayloadCodec()

    def decode(self, payload: JSONObject) -> UserRegistered:
        return decode_payload(self.codec, payload)

    def test_exact_wire_contract_and_json_round_trip_for_all_roles(self) -> None:
        for role in Role:
            for user_id in (1, 7, 2**63):
                for username in ("alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                    with self.subTest(role=role, user_id=user_id, username=username):
                        event = UserRegistered(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            user_id=user_id,
                            username=username,
                            role=role,
                        )
                        encoded = self.codec.encode(event)
                        self.assertEqual(
                            encoded, {"user_id": user_id, "username": username, "role": role.value}
                        )
                        self.assertIs(type(encoded["user_id"]), int)
                        restored = self.decode(json_round_trip(encoded))
                        self.assertIs(type(restored), UserRegistered)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.role, role)

    def test_requires_all_keys_and_rejects_empty_payload(self) -> None:
        assert_required_keys(self, self.decode, make_authenticated_payload())

    def test_rejects_extra_credentials_actor_and_metadata_fields(self) -> None:
        for field in ("password", "password_hash", "actor_user_id", "event_id"):
            with self.subTest(field=field):
                payload = make_authenticated_payload()
                payload[field] = "unexpected"
                with self.assertRaisesRegex(ValueError, f"Unexpected fields:.*{field}"):
                    self.decode(payload)

    def test_rejects_non_positive_user_ids(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value):
                payload = make_authenticated_payload()
                payload["user_id"] = value
                with self.assertRaisesRegex(ValueError, "user_id must be a positive integer"):
                    self.decode(payload)

    def test_rejects_wrong_field_types_without_coercion(self) -> None:
        invalid_by_field: dict[str, tuple[JSONValue, ...]] = {
            "user_id": (None, True, False, 1.0, "7", "", [], {}),
            "username": (None, True, False, 7, 1.5, [], {}),
            "role": (None, True, False, 7, 1.5, [], {}),
        }
        for field, values in invalid_by_field.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    payload = make_authenticated_payload()
                    payload[field] = value
                    with self.assertRaisesRegex(TypeError, field):
                        self.decode(payload)

    def test_unknown_roles_raise_value_error(self) -> None:
        for role in ("", "UNKNOWN", "manager", " MANAGER ", "1"):
            with self.subTest(role=role):
                payload = make_authenticated_payload()
                payload["role"] = role
                with self.assertRaises(ValueError):
                    self.decode(payload)

    def test_payload_and_event_are_independent(self) -> None:
        payload = make_authenticated_payload()
        event = self.decode(payload)
        self.assertEqual(payload, make_authenticated_payload())
        payload["username"] = "changed"
        self.assertEqual(event.username, "alice")
        encoded = self.codec.encode(event)
        encoded["role"] = "EMPLOYEE"
        self.assertEqual(self.codec.encode(event), make_authenticated_payload())

    def test_registry_distinguishes_registration_from_authentication(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserRegistered, self.codec)
        registry.register(UserAuthenticated, UserAuthenticatedEventPayloadCodec())
        event = self.decode(make_authenticated_payload())
        adapter = registry.for_identity("user_registered", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserRegistered)
        self.assertEqual(adapter.event_version, 1)
        self.assertIsNot(adapter, registry.for_identity("user_authenticated", 1))
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
            registry.for_identity("user_registered", 2)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, make_authenticated_payload())
