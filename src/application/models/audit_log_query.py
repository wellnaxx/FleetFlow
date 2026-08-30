"""Audit-log read query and filter models."""

from dataclasses import dataclass, field
from datetime import datetime

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.messaging.query import Query
from src.application.models.audit_validation import require_ordered_optional_datetime_range
from src.application.use_cases.pagination import PageQuery
from src.shared.validation import require_datetime, require_enum, require_non_empty_str, require_positive_int


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditLogFilter:
    """Optional filters for browsing persisted audit records.

    Filters are exact-match except for timestamp bounds, which are inclusive.
    String filters are stripped and rejected when empty. Enum filters must be
    supplied as enum instances, leaving raw string parsing to HTTP/CLI
    adapters.

    Attributes:
        event_type: Concrete event class name to match.
        resource_type: Normalized resource family to match.
        resource_id: Normalized text resource id to match.
        action: Normalized audit action to match.
        actor_user_id: Authenticated actor id to match.
        actor_username: Authenticated actor username to match.
        source: Event source to match.
        occurred_from: Inclusive lower bound for event occurrence time.
        occurred_to: Inclusive upper bound for event occurrence time.
        created_from: Inclusive lower bound for audit persistence time.
        created_to: Inclusive upper bound for audit persistence time.
    """

    event_type: str | None = None
    resource_type: AuditResourceType | None = None
    resource_id: str | None = None
    action: AuditAction | None = None
    actor_user_id: int | None = None
    actor_username: str | None = None
    source: EventSource | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None

    def __post_init__(self) -> None:
        """Validate and normalize audit-log filters."""
        if self.event_type is not None:
            object.__setattr__(self, "event_type", require_non_empty_str(self.event_type, "event_type"))

        if self.resource_type is not None:
            require_enum(self.resource_type, "resource_type", AuditResourceType)

        if self.resource_id is not None:
            object.__setattr__(self, "resource_id", require_non_empty_str(self.resource_id, "resource_id"))

        if self.action is not None:
            require_enum(self.action, "action", AuditAction)

        if self.actor_user_id is not None:
            require_positive_int(self.actor_user_id, "actor_user_id")

        if self.actor_username is not None:
            object.__setattr__(
                self,
                "actor_username",
                require_non_empty_str(self.actor_username, "actor_username"),
            )

        if self.source is not None:
            require_enum(self.source, "source", EventSource)

        if self.occurred_from is not None:
            require_datetime(self.occurred_from, "occurred_from")

        if self.occurred_to is not None:
            require_datetime(self.occurred_to, "occurred_to")

        if self.created_from is not None:
            require_datetime(self.created_from, "created_from")

        if self.created_to is not None:
            require_datetime(self.created_to, "created_to")

        require_ordered_optional_datetime_range(self.occurred_from, self.occurred_to, "occurred")
        require_ordered_optional_datetime_range(self.created_from, self.created_to, "created")


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditLogQuery(Query):
    """Paginated audit-log read request.

    This model is also the message dispatched through the application query
    bus. Keeping one request type prevents adapter, handler, and use-case
    pagination or filtering contracts from drifting apart.

    Attributes:
        page: Pagination options for the audit listing.
        filters: Optional audit filters applied before pagination.
    """

    page: PageQuery = field(default_factory=PageQuery)
    filters: AuditLogFilter = field(default_factory=AuditLogFilter)
