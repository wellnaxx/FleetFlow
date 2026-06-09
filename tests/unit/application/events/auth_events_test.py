"""Tests for authentication and authorization application event shapes."""

from dataclasses import fields
from datetime import datetime

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


def test_user_registered_contains_identity_without_contact_information() -> None:
    event = UserRegistered(
        user_id=7,
        username="dispatcher",
        role=Role.EMPLOYEE,
        occurred_at=datetime(2026, 6, 9, 10, 0),
    )

    assert isinstance(event, ApplicationEvent)
    assert event.role is Role.EMPLOYEE
    assert {field.name for field in fields(event)} == {
        "event_id",
        "occurred_at",
        "recorded_at",
        "user_id",
        "username",
        "role",
    }


def test_password_reset_does_not_embed_actor_context() -> None:
    event = UserPasswordReset(
        user_id=7,
        username="dispatcher",
        occurred_at=datetime(2026, 6, 9, 10, 0),
    )

    assert {field.name for field in fields(event)} == {
        "event_id",
        "occurred_at",
        "recorded_at",
        "user_id",
        "username",
    }


def test_authentication_and_session_events_describe_distinct_facts() -> None:
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

    assert authenticated.role is Role.EMPLOYEE
    assert session_ended.user_id == authenticated.user_id


def test_token_revocation_uses_typed_reason() -> None:
    event = UserTokensRevoked(
        user_id=7,
        username="dispatcher",
        reason=TokenRevocationReason.PASSWORD_CHANGE,
        occurred_at=datetime(2026, 6, 9, 10, 0),
    )

    assert event.reason is TokenRevocationReason.PASSWORD_CHANGE


def test_authorization_denial_supports_multiple_required_permissions() -> None:
    event = AuthorizationDenied(
        user_id=7,
        username="dispatcher",
        required_permissions=(
            Permission.ROUTE_REMOVE,
            Permission.ROUTE_VIEW,
        ),
        occurred_at=datetime(2026, 6, 9, 10, 0),
    )

    assert event.required_permissions == (
        Permission.ROUTE_REMOVE,
        Permission.ROUTE_VIEW,
    )
