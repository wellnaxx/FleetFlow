"""Normalized action names used by audit-log records."""

from enum import StrEnum


class AuditAction(StrEnum):
    """Stable audit action vocabulary derived from published event types.

    These values are stored with audit records for querying and reporting.
    They intentionally describe user/business meaning rather than Python event
    class names; the original concrete event type is stored separately.
    """

    # Generic entity lifecycle actions.
    CREATED = "created"
    REMOVED = "removed"
    SCHEDULED = "scheduled"
    STARTED = "started"
    COMPLETED = "completed"

    # Route/package/truck logistics actions.
    ASSIGNED_TO_ROUTE = "assigned_to_route"
    DETACHED_FROM_ROUTE = "detached_from_route"
    ASSIGNED_TO_TRUCK = "assigned_to_truck"
    RELEASED_TRUCK = "released_truck"

    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    RECONCILED = "reconciled"

    # Authentication and user-management actions.
    REGISTERED = "registered"
    REGISTRATION_REJECTED = "registration_rejected"
    AUTHENTICATED = "authenticated"
    LOGIN_REJECTED = "login_rejected"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_CHANGE_REJECTED = "password_change_rejected"
    PASSWORD_RESET = "password_reset"
    PASSWORD_RESET_REJECTED = "password_reset_rejected"
    SESSION_ENDED = "session_ended"
    TOKENS_REVOKED = "tokens_revoked"

    AUTHORIZATION_DENIED = "authorization_denied"

    # World-state persistence and runtime actions.
    EXPORTED = "exported"
    EXPORT_FAILED = "export_failed"
    IMPORTED = "imported"
    IMPORT_FAILED = "import_failed"
    CORRUPTION_DETECTED = "corruption_detected"
    SNAPSHOT_QUARANTINED = "snapshot_quarantined"
    RUNTIME_SWAPPED = "runtime_swapped"
    STARTUP_RESTORED = "startup_restored"
    STARTUP_RESTORE_SKIPPED = "startup_restore_skipped"
    STARTUP_RESTORE_FAILED = "startup_restore_failed"
    ADVANCED = "advanced"

    # Startup/composition actions.
    SEEDED = "seeded"
