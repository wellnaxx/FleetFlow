"""Tests for authentication and authorization application event shapes."""

import unittest
from dataclasses import fields
from datetime import datetime

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.events.auth_events import (
    AuthorizationDenied,
    UserAuthenticated,
    UserPasswordReset,
    UserRegistered,
    UserSessionEnded,
    UserTokensRevoked,
)
from src.application.events.base import ApplicationEvent
from src.domain.enums.auth import Permission, Role


class AuthEventShould(unittest.TestCase):
    def test_user_registered_contains_identity_without_contact_information(self) -> None:
        event = UserRegistered(
            user_id=7,
            username="dispatcher",
            role=Role.EMPLOYEE,
            occurred_at=datetime(2026, 6, 9, 10, 0),
        )

        self.assertIsInstance(event, ApplicationEvent)
        self.assertIs(event.role, Role.EMPLOYEE)
        self.assertEqual(
            {field.name for field in fields(event)},
            {
                "event_id",
                "occurred_at",
                "recorded_at",
                "user_id",
                "username",
                "role",
            },
        )

    def test_password_reset_does_not_embed_actor_context(self) -> None:
        event = UserPasswordReset(
            user_id=7,
            username="dispatcher",
            occurred_at=datetime(2026, 6, 9, 10, 0),
        )

        self.assertEqual(
            {field.name for field in fields(event)},
            {
                "event_id",
                "occurred_at",
                "recorded_at",
                "user_id",
                "username",
            },
        )

    def test_authentication_and_session_events_describe_distinct_facts(self) -> None:
        occurred_at = datetime(2026, 6, 9, 10, 0)

        authenticated = UserAuthenticated(
            user_id=7,
            username="dispatcher",
            role=Role.EMPLOYEE,
            occurred_at=occurred_at,
        )
        session_ended = UserSessionEnded(
            user_id=7,
            username="dispatcher",
            occurred_at=occurred_at,
        )

        self.assertIs(authenticated.role, Role.EMPLOYEE)
        self.assertEqual(session_ended.user_id, authenticated.user_id)

    def test_token_revocation_uses_typed_reason(self) -> None:
        event = UserTokensRevoked(
            user_id=7,
            username="dispatcher",
            reason=TokenRevocationReason.PASSWORD_CHANGE,
            occurred_at=datetime(2026, 6, 9, 10, 0),
        )

        self.assertIs(event.reason, TokenRevocationReason.PASSWORD_CHANGE)

    def test_authorization_denial_supports_multiple_required_permissions(self) -> None:
        event = AuthorizationDenied(
            attempted_operation=AuthorizationOperation.ROUTE_REMOVE,
            target_resource_type=AuditResourceType.ROUTE,
            target_resource_id="42",
            required_permissions=(
                Permission.ROUTE_REMOVE,
                Permission.ROUTE_VIEW,
            ),
            occurred_at=datetime(2026, 6, 9, 10, 0),
        )

        self.assertEqual(
            event.required_permissions,
            (
                Permission.ROUTE_REMOVE,
                Permission.ROUTE_VIEW,
            ),
        )
        self.assertIs(event.attempted_operation, AuthorizationOperation.ROUTE_REMOVE)
        self.assertIs(event.target_resource_type, AuditResourceType.ROUTE)
        self.assertEqual(event.target_resource_id, "42")
