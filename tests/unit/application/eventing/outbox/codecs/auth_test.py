"""Authorization-denied and user-authenticated payload contract tests."""

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.eventing.outbox.codecs.auth import (
    AuthorizationDeniedEventPayloadCodec,
    UserAuthenticatedEventPayloadCodec,
)
from src.application.eventing.outbox.errors import EventCodecNotFoundError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.application.events.auth_events import AuthorizationDenied, UserAuthenticated
from src.domain.enums.auth import Permission, Role
from src.shared.json_types import JSONObject, JSONValue

EVENT_ID = UUID("12345678-1234-4678-9234-567812345678")
OCCURRED_AT = datetime(2030, 1, 2, 3, 4, 5, 123456)
RECORDED_AT = datetime(2030, 1, 2, 1, 4, 5, 654321, tzinfo=UTC)


def make_authenticated_payload() -> JSONObject:
    return {"user_id": 7, "username": "alice", "role": "MANAGER"}


def make_payload() -> JSONObject:
    return {
        "attempted_operation": "package.view",
        "target_resource_type": "package",
        "target_resource_id": "7",
        "required_permissions": ["PACKAGE_VIEW"],
    }


class UserAuthenticatedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = UserAuthenticatedEventPayloadCodec()

    def decode(self, payload: JSONObject) -> UserAuthenticated:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

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
                        payload = cast(JSONObject, json.loads(json.dumps(self.codec.encode(event))))
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
            adapter.encode(event), event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )
        self.assertEqual(restored, event)
        with self.assertRaises(EventCodecNotFoundError):
            registry.for_identity("user_authenticated", 2)

    def test_event_constructor_rejects_invalid_metadata(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
            ("event_id", None, TypeError),
            ("event_id", str(EVENT_ID), TypeError),
            ("occurred_at", "2030-01-02", TypeError),
            ("recorded_at", None, TypeError),
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
                        make_authenticated_payload(),
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )


class AuthorizationDeniedCodecShould(unittest.TestCase):
    def setUp(self) -> None:
        self.codec = AuthorizationDeniedEventPayloadCodec()

    def decode(self, payload: JSONObject) -> AuthorizationDenied:
        return self.codec.decode(
            payload, event_id=EVENT_ID, occurred_at=OCCURRED_AT, recorded_at=RECORDED_AT
        )

    def test_encodes_exact_wire_contract_without_metadata(self) -> None:
        event = AuthorizationDenied(
            event_id=EVENT_ID,
            occurred_at=OCCURRED_AT,
            recorded_at=RECORDED_AT,
            attempted_operation=AuthorizationOperation.PACKAGE_VIEW,
            target_resource_type=AuditResourceType.PACKAGE,
            target_resource_id="7",
            required_permissions=(Permission.PACKAGE_VIEW,),
        )
        self.assertEqual(self.codec.encode(event), make_payload())

    def test_json_round_trip_preserves_fields_and_metadata(self) -> None:
        permission_sets = (
            (),
            (Permission.AUTHENTICATED,),
            tuple(Permission),
            (Permission.PACKAGE_VIEW, Permission.ADMIN_USER, Permission.PACKAGE_VIEW),
        )
        for target in (None, "7", "", "  literal id  ", "identifier-\u03b1"):
            for permissions in permission_sets:
                with self.subTest(target=target, permissions=permissions):
                    original = AuthorizationDenied(
                        event_id=EVENT_ID,
                        occurred_at=OCCURRED_AT,
                        recorded_at=RECORDED_AT,
                        attempted_operation=AuthorizationOperation.PACKAGE_VIEW,
                        target_resource_type=AuditResourceType.PACKAGE,
                        target_resource_id=target,
                        required_permissions=permissions,
                    )
                    payload = cast(JSONObject, json.loads(json.dumps(self.codec.encode(original))))
                    restored = self.decode(payload)
                    self.assertEqual(restored, original)
                    self.assertIsInstance(restored.required_permissions, tuple)

    def test_supports_every_operation_and_resource_enum_value(self) -> None:
        for operation in AuthorizationOperation:
            for resource in AuditResourceType:
                with self.subTest(operation=operation, resource=resource):
                    payload = make_payload()
                    payload["attempted_operation"] = operation.value
                    payload["target_resource_type"] = resource.value
                    event = self.decode(payload)
                    self.assertIs(event.attempted_operation, operation)
                    self.assertIs(event.target_resource_type, resource)
                    self.assertEqual(self.codec.encode(event), payload)

    def test_registry_resolves_version_two_and_rejects_other_versions(self) -> None:
        registry = EventOutboxCodecRegistry()
        registry.register(AuthorizationDenied, self.codec)
        event = self.decode(make_payload())
        adapter = registry.for_identity("authorization_denied", 2)
        self.assertIs(adapter, registry.for_event(event))
        self.assertIs(adapter.event_class, AuthorizationDenied)
        self.assertEqual(adapter.encode(event), make_payload())
        for version in (1, 3):
            with self.subTest(version=version), self.assertRaises(EventCodecNotFoundError):
                registry.for_identity("authorization_denied", version)

    def test_requires_each_key_including_nullable_target(self) -> None:
        for key in make_payload():
            with self.subTest(key=key):
                payload = make_payload()
                del payload[key]
                with self.assertRaisesRegex(ValueError, f"Missing fields:.*{key}"):
                    self.decode(payload)

    def test_rejects_empty_payload(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.decode({})

    def test_reports_extra_fields_in_sorted_order(self) -> None:
        payload = make_payload()
        payload.update({"z_extra": None, "a_extra": None})
        with self.assertRaises(ValueError) as ctx:
            self.decode(payload)
        self.assertEqual(str(ctx.exception), "Unexpected fields: ['a_extra', 'z_extra']")

    def test_rejects_wrong_types_for_enum_fields_and_target(self) -> None:
        invalid: tuple[JSONValue, ...] = (0, True, 1.5, [], {})
        for field in ("attempted_operation", "target_resource_type", "target_resource_id"):
            values = (*invalid, None) if field != "target_resource_id" else invalid
            for value in values:
                with self.subTest(field=field, value=value):
                    payload = make_payload()
                    payload[field] = value
                    with self.assertRaisesRegex(TypeError, field):
                        self.decode(payload)

    def test_rejects_unknown_enum_values_without_normalizing(self) -> None:
        for field in ("attempted_operation", "target_resource_type"):
            for value in ("", "unknown", "PACKAGE_VIEW", "PACKAGE", " package "):
                with self.subTest(field=field, value=value):
                    payload = make_payload()
                    payload[field] = value
                    with self.assertRaises(ValueError):
                        self.decode(payload)

    def test_requires_permission_list(self) -> None:
        values: tuple[object, ...] = (None, "PACKAGE_VIEW", {}, 1, True, ("PACKAGE_VIEW",))
        for value in values:
            with self.subTest(value=value):
                payload = make_payload()
                payload["required_permissions"] = cast(JSONValue, value)
                with self.assertRaisesRegex(TypeError, "required_permissions: expected list"):
                    self.decode(payload)

    def test_requires_string_permission_entries_and_reports_index(self) -> None:
        values: tuple[JSONValue, ...] = (None, True, 1, 1.5, [], {})
        for value in values:
            with self.subTest(value=value):
                payload = make_payload()
                payload["required_permissions"] = ["PACKAGE_VIEW", value]
                with self.assertRaisesRegex(TypeError, r"required_permissions\[1\]: expected str"):
                    self.decode(payload)

    def test_unknown_permission_names_report_index_and_preserve_cause(self) -> None:
        for name in ("", "UNKNOWN", "package_view", " PACKAGE_VIEW ", "1"):
            with self.subTest(name=name):
                payload = make_payload()
                payload["required_permissions"] = ["PACKAGE_VIEW", name]
                with self.assertRaises(ValueError) as ctx:
                    self.decode(payload)
                self.assertEqual(
                    str(ctx.exception), f"required_permissions[1]: unknown permission name {name!r}"
                )
                self.assertIsInstance(ctx.exception.__cause__, KeyError)

    def test_payload_and_event_collections_are_independent(self) -> None:
        payload = make_payload()
        event = self.decode(payload)
        self.assertEqual(payload, make_payload())
        cast(list[JSONValue], payload["required_permissions"]).clear()
        self.assertEqual(event.required_permissions, (Permission.PACKAGE_VIEW,))
        encoded = self.codec.encode(event)
        cast(list[JSONValue], encoded["required_permissions"]).clear()
        self.assertEqual(self.codec.encode(event), make_payload())

    def test_event_constructor_validates_supplied_metadata(self) -> None:
        cases: tuple[tuple[str, object, type[Exception]], ...] = (
            ("event_id", str(EVENT_ID), TypeError),
            ("occurred_at", "2030-01-02", TypeError),
            ("recorded_at", None, TypeError),
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
                        make_payload(),
                        event_id=cast(UUID, metadata["event_id"]),
                        occurred_at=cast(datetime, metadata["occurred_at"]),
                        recorded_at=cast(datetime, metadata["recorded_at"]),
                    )
