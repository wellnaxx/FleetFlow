"""Audit descriptor mappings for authentication and authorization events."""

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.events.auth_events import (
    AuthorizationDenied,
    UserAuthenticated,
    UserLoginRejected,
    UserPasswordChanged,
    UserPasswordChangeRejected,
    UserPasswordReset,
    UserPasswordResetRejected,
    UserRegistered,
    UserRegistrationRejected,
    UserSessionEnded,
    UserTokensRevoked,
)
from src.application.models.audit_descriptor import AuditDescriptor
from src.application.services.audit_mapping.mapper import AuditDescriptorMapping, audit_mapping
from src.shared.json_serialization import optional_id


def map_user_registered(event: UserRegistered) -> AuditDescriptor:
    """Map successful user registration."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=str(event.user_id),
        action=AuditAction.REGISTERED,
        payload_json={
            "user_id": str(event.user_id),
            "username": event.username,
            "role": event.role.value,
        },
    )


def map_user_registration_rejected(event: UserRegistrationRejected) -> AuditDescriptor:
    """Map rejected user registration."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=None,
        action=AuditAction.REGISTRATION_REJECTED,
        payload_json={"username": event.username, "reason": event.reason.value},
    )


def map_user_password_changed(event: UserPasswordChanged) -> AuditDescriptor:
    """Map successful password change."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=str(event.user_id),
        action=AuditAction.PASSWORD_CHANGED,
        payload_json={"user_id": str(event.user_id), "username": event.username},
    )


def map_user_password_change_rejected(event: UserPasswordChangeRejected) -> AuditDescriptor:
    """Map rejected password change."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=optional_id(event.user_id),
        action=AuditAction.PASSWORD_CHANGE_REJECTED,
        payload_json={
            "user_id": optional_id(event.user_id),
            "username": event.username,
            "reason": event.reason.value,
        },
    )


def map_user_password_reset(event: UserPasswordReset) -> AuditDescriptor:
    """Map successful password reset."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=str(event.user_id),
        action=AuditAction.PASSWORD_RESET,
        payload_json={"user_id": str(event.user_id), "username": event.username},
    )


def map_user_password_reset_rejected(event: UserPasswordResetRejected) -> AuditDescriptor:
    """Map rejected password reset."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=optional_id(event.user_id),
        action=AuditAction.PASSWORD_RESET_REJECTED,
        payload_json={
            "user_id": optional_id(event.user_id),
            "username": event.username,
            "reason": event.reason.value,
        },
    )


def map_user_authenticated(event: UserAuthenticated) -> AuditDescriptor:
    """Map successful authentication."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=str(event.user_id),
        action=AuditAction.AUTHENTICATED,
        payload_json={
            "user_id": str(event.user_id),
            "username": event.username,
            "role": event.role.value,
        },
    )


def map_user_login_rejected(event: UserLoginRejected) -> AuditDescriptor:
    """Map rejected authentication."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=optional_id(event.user_id),
        action=AuditAction.LOGIN_REJECTED,
        payload_json={
            "user_id": optional_id(event.user_id),
            "username": event.username,
            "reason": event.reason.value,
        },
    )


def map_user_session_ended(event: UserSessionEnded) -> AuditDescriptor:
    """Map session termination."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=str(event.user_id),
        action=AuditAction.SESSION_ENDED,
        payload_json={"user_id": str(event.user_id), "username": event.username},
    )


def map_user_tokens_revoked(event: UserTokensRevoked) -> AuditDescriptor:
    """Map token revocation."""
    return AuditDescriptor(
        resource_type=AuditResourceType.USER,
        resource_id=str(event.user_id),
        action=AuditAction.TOKENS_REVOKED,
        payload_json={
            "user_id": str(event.user_id),
            "username": event.username,
            "reason": event.reason.value,
        },
    )


def map_authorization_denied(event: AuthorizationDenied) -> AuditDescriptor:
    """Map a denied authorization attempt against its target resource."""
    return AuditDescriptor(
        resource_type=event.target_resource_type,
        resource_id=event.target_resource_id,
        action=AuditAction.AUTHORIZATION_DENIED,
        payload_json={
            "attempted_operation": event.attempted_operation.value,
            "required_permissions": [permission.name for permission in event.required_permissions],
        },
    )


AUTH_AUDIT_MAPPINGS: tuple[AuditDescriptorMapping, ...] = (
    audit_mapping(UserRegistered, map_user_registered),
    audit_mapping(UserRegistrationRejected, map_user_registration_rejected),
    audit_mapping(UserPasswordChanged, map_user_password_changed),
    audit_mapping(UserPasswordChangeRejected, map_user_password_change_rejected),
    audit_mapping(UserPasswordReset, map_user_password_reset),
    audit_mapping(UserPasswordResetRejected, map_user_password_reset_rejected),
    audit_mapping(UserAuthenticated, map_user_authenticated),
    audit_mapping(UserLoginRejected, map_user_login_rejected),
    audit_mapping(UserSessionEnded, map_user_session_ended),
    audit_mapping(UserTokensRevoked, map_user_tokens_revoked),
    audit_mapping(AuthorizationDenied, map_authorization_denied),
)
