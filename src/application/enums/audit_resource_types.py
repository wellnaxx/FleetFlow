"""Normalized resource families used by audit-log records."""

from enum import StrEnum


class AuditResourceType(StrEnum):
    """Stable audit resource vocabulary for filtering and reporting.

    Resource types group concrete event payloads into business-facing
    categories. The resource id remains text because FleetFlow resources may be
    integer ids, usernames, paths, or system-wide resources depending on the
    event.
    """

    AUDIT_LOG = "audit_log"
    CUSTOMER = "customer"
    PACKAGE = "package"
    ROUTE = "route"
    TRUCK = "truck"
    USER = "user"
    AUTHORIZATION = "authorization"
    WORLD_STATE = "world_state"
    FLEET = "fleet"
