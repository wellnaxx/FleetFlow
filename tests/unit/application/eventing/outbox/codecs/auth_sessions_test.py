"""Authentication, session termination, and token revocation outbox payload contract tests."""

import unittest

from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.enums.user_login_rejection_reasons import UserLoginRejectionReason
from src.application.eventing.outbox.codecs.auth_passwords import UserPasswordChangedEventPayloadCodec
from src.application.eventing.outbox.codecs.auth_sessions import (
    UserAuthenticatedEventPayloadCodec,
    UserLoginRejectedEventPayloadCodec,
    UserSessionEndedEventPayloadCodec,
    UserTokensRevokedEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.auth_events import (
    UserAuthenticated,
    UserLoginRejected,
    UserPasswordChanged,
    UserSessionEnded,
    UserTokensRevoked,
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


class UserTokensRevokedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserTokensRevokedEventPayloadCodec()

    def make_payload(self) -> JSONObject:
        return {"user_id": 7, "username": "alice", "reason": "USER_LOGOUT"}

    def decode(self, payload: JSONObject) -> UserTokensRevoked:
        return decode_payload(self.codec, payload)

    def test_exact_wire_contract_and_json_round_trip_for_all_revocation_reasons(self) -> None:
        for reason in TokenRevocationReason:
            for user_id in (1, 7, 2**63):
                for username in ("alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                    with self.subTest(reason=reason, user_id=user_id, username=username):
                        event = UserTokensRevoked(
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
                        self.assertIs(type(encoded["user_id"]), int)
                        restored = self.decode(json_round_trip(encoded))
                        self.assertIs(type(restored), UserTokensRevoked)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.reason, reason)

    def test_requires_every_key_and_rejects_empty_payload(self) -> None:
        assert_required_keys(self, self.decode, self.make_payload())

    def test_rejects_extra_credentials_tokens_and_metadata(self) -> None:
        for field in (
            "password", "password_hash", "access_token", "refresh_token", "event_id", "actor_user_id"
        ):
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
            "", "UNKNOWN", "user_logout", " USER_LOGOUT ", "1", "INVALID_PASSWORD", "USER_NOT_FOUND"
        ):
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
        encoded["reason"] = "PASSWORD_RESET"
        self.assertEqual(self.codec.encode(event), self.make_payload())

    def test_registry_distinguishes_token_revocation_from_session_end(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserTokensRevoked, self.codec)
        registry.register(UserSessionEnded, UserSessionEndedEventPayloadCodec())
        event = self.decode(self.make_payload())
        adapter = registry.for_identity("user_tokens_revoked", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserTokensRevoked)
        self.assertEqual(adapter.event_version, 1)
        self.assertIsNot(adapter, registry.for_identity("user_session_ended", 1))
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
            registry.for_identity("user_tokens_revoked", 2)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.make_payload())


class UserSessionEndedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserSessionEndedEventPayloadCodec()

    def make_payload(self) -> JSONObject:
        return {"user_id": 7, "username": "alice"}

    def decode(self, payload: JSONObject) -> UserSessionEnded:
        return decode_payload(self.codec, payload)

    def test_exact_wire_contract_and_json_round_trip_preserve_identity_and_metadata(self) -> None:
        for user_id in (1, 7, 2**63):
            for username in ("alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                with self.subTest(user_id=user_id, username=username):
                    event = UserSessionEnded(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        user_id=user_id,
                        username=username,
                    )
                    encoded = self.codec.encode(event)
                    self.assertEqual(encoded, {"user_id": user_id, "username": username})
                    self.assertIs(type(encoded["user_id"]), int)
                    restored = self.decode(json_round_trip(encoded))
                    self.assertIs(type(restored), UserSessionEnded)
                    self.assertEqual(restored, event)

    def test_requires_every_key_and_rejects_empty_payload(self) -> None:
        assert_required_keys(self, self.decode, self.make_payload())

    def test_rejects_extra_credentials_tokens_and_metadata(self) -> None:
        for field in ("password", "password_hash", "access_token", "refresh_token", "event_id", "reason"):
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

    def test_registry_distinguishes_session_end_from_password_change(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserSessionEnded, self.codec)
        registry.register(UserPasswordChanged, UserPasswordChangedEventPayloadCodec())
        event = self.decode(self.make_payload())
        adapter = registry.for_identity("user_session_ended", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserSessionEnded)
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
            registry.for_identity("user_session_ended", 2)

    def test_event_constructor_validates_supplied_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.make_payload())


class UserLoginRejectedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserLoginRejectedEventPayloadCodec()

    def make_payload(self) -> JSONObject:
        return {"user_id": 7, "username": "alice", "reason": "INVALID_PASSWORD"}

    def decode(self, payload: JSONObject) -> UserLoginRejected:
        return decode_payload(self.codec, payload)

    def test_encodes_exact_wire_contract_including_explicit_nulls(self) -> None:
        for user_id, username in ((7, "alice"), (None, None), (7, None), (None, "alice")):
            with self.subTest(user_id=user_id, username=username):
                event = UserLoginRejected(
                    event_id=EVENT_ID,
                    occurred_at=OCCURRED_AT,
                    recorded_at=RECORDED_AT,
                    user_id=user_id,
                    username=username,
                    reason=UserLoginRejectionReason.INVALID_PASSWORD,
                )
                self.assertEqual(
                    self.codec.encode(event),
                    {"user_id": user_id, "username": username, "reason": "INVALID_PASSWORD"},
                )

    def test_json_round_trip_preserves_all_reasons_and_nullable_identity_combinations(self) -> None:
        for reason in UserLoginRejectionReason:
            for user_id in (None, 1, 2**63):
                for username in (None, "alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                    with self.subTest(reason=reason, user_id=user_id, username=username):
                        event = UserLoginRejected(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            user_id=user_id,
                            username=username,
                            reason=reason,
                        )
                        payload = json_round_trip(self.codec.encode(event))
                        restored = self.decode(payload)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.reason, reason)

    def test_requires_every_key_even_when_identity_values_are_null(self) -> None:
        for field in self.make_payload():
            with self.subTest(field=field):
                payload: JSONObject = {"user_id": None, "username": None, "reason": "USER_NOT_FOUND"}
                del payload[field]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{field}"):
                    self.decode(payload)

    def test_rejects_empty_payload_and_extra_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})
        payload = self.make_payload()
        payload.update({"password": "unexpected", "event_id": str(EVENT_ID)})
        with self.assertRaises(ValueError) as ctx:
            self.decode(payload)
        self.assertEqual(str(ctx.exception), "Unexpected fields: ['event_id', 'password']")

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

    def test_unknown_reasons_raise_value_error(self) -> None:
        for reason in ("", "UNKNOWN", "invalid_password", " INVALID_PASSWORD ", "1"):
            with self.subTest(reason=reason):
                payload = self.make_payload()
                payload["reason"] = reason
                with self.assertRaises(ValueError):
                    self.decode(payload)

    def test_codec_does_not_mutate_or_retain_input_payload(self) -> None:
        payload = self.make_payload()
        event = self.decode(payload)
        self.assertEqual(payload, self.make_payload())
        payload["username"] = "changed"
        self.assertEqual(event.username, "alice")
        encoded = self.codec.encode(event)
        encoded["reason"] = "USER_NOT_FOUND"
        self.assertEqual(self.codec.encode(event), self.make_payload())

    def test_registry_resolves_exact_version_and_preserves_decoded_event(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserLoginRejected, self.codec)
        event = self.decode(self.make_payload())
        adapter = registry.for_identity("user_login_rejected", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserLoginRejected)
        self.assertEqual(adapter.event_version, 1)
        restored = adapter.decode(
            registry.for_event(event).encode(event),
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
        )
        self.assertEqual(restored, event)
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("user_login_rejected", 2)

    def test_event_constructor_validates_supplied_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, self.make_payload())


class UserAuthenticatedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserAuthenticatedEventPayloadCodec()

    def decode(self, payload: JSONObject) -> UserAuthenticated:
        return decode_payload(self.codec, payload)

    def test_encodes_exact_contract_with_integer_id_and_role_value(self) -> None:
        event = UserAuthenticated(
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
            user_id=7,
            username="alice",
            role=Role.MANAGER,
        )
        self.assertEqual(self.codec.encode(event), make_authenticated_payload())
        self.assertIs(type(self.codec.encode(event)["user_id"]), int)

    def test_json_round_trip_preserves_all_roles_ids_usernames_and_metadata(self) -> None:
        for role in Role:
            for user_id in (1, 7, 2**63):
                for username in ("alice", "MiXeD", "", "   ", "  alice  ", "user-\u03b1"):
                    with self.subTest(role=role, user_id=user_id, username=username):
                        event = UserAuthenticated(
                            event_id=EVENT_ID,
                            occurred_at=OCCURRED_AT,
                            recorded_at=RECORDED_AT,
                            user_id=user_id,
                            username=username,
                            role=role,
                        )
                        payload = json_round_trip(self.codec.encode(event))
                        restored = self.decode(payload)
                        self.assertEqual(restored, event)
                        self.assertIs(restored.role, role)

    def test_requires_each_payload_key(self) -> None:
        for key in make_authenticated_payload():
            with self.subTest(key=key):
                payload = make_authenticated_payload()
                del payload[key]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{key}"):
                    self.decode(payload)

    def test_rejects_empty_payload_and_extra_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})
        payload = make_authenticated_payload()
        payload["event_id"] = str(EVENT_ID)
        with self.assertRaisesRegex(ValueError, "Unexpected fields:.*event_id"):
            self.decode(payload)

    def test_rejects_non_positive_user_ids(self) -> None:
        for value in (0, -1, -(2**63)):
            with self.subTest(value=value):
                payload = make_authenticated_payload()
                payload["user_id"] = value
                with self.assertRaisesRegex(ValueError, "user_id must be a positive integer"):
                    self.decode(payload)

    def test_rejects_invalid_field_types_without_coercion(self) -> None:
        invalid_by_field: dict[str, tuple[JSONValue, ...]] = {
            "user_id": (None, True, False, 1.0, "7", "", [], {}),
            "username": (None, True, 7, 1.5, [], {}),
            "role": (None, True, 7, 1.5, [], {}),
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

    def test_encoding_and_decoding_do_not_share_mutable_payload(self) -> None:
        payload = make_authenticated_payload()
        event = self.decode(payload)
        self.assertEqual(payload, make_authenticated_payload())
        payload["username"] = "changed"
        self.assertEqual(event.username, "alice")
        encoded = self.codec.encode(event)
        encoded["user_id"] = 999
        self.assertEqual(self.codec.encode(event), make_authenticated_payload())

    def test_registry_resolves_version_one_codec_in_both_directions(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(UserAuthenticated, self.codec)
        event = self.decode(make_authenticated_payload())
        adapter = registry.for_identity("user_authenticated", 1)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, UserAuthenticated)
        restored = adapter.decode(
            registry.for_event(event).encode(event),
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
        )
        self.assertEqual(restored, event)
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("user_authenticated", 2)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        assert_invalid_metadata(self, self.codec, make_authenticated_payload())
