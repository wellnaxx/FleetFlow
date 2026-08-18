"""HTTP routes for browsing audit-log records."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.driving.http.dependencies.message_buses import get_authenticated_query_bus
from src.adapters.driving.http.schemas.audit import AuditRecordPageResponse
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_log_query import AuditLogFilter, AuditLogQuery
from src.application.queries.audit.view_audits import VIEW_AUDITS
from src.application.use_cases.pagination import PageQuery
from src.ports.input.query_bus import QueryBus

audit_router = APIRouter(prefix="/audit", tags=["audit"])


def get_audit_log_filter(
    event_type: str | None = None,
    resource_type: AuditResourceType | None = None,
    resource_id: str | None = None,
    action: AuditAction | None = None,
    actor_user_id: Annotated[int | None, Query(ge=1)] = None,
    actor_username: str | None = None,
    source: EventSource | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> AuditLogFilter:
    """Build an application audit filter from HTTP query parameters.

    Args:
        event_type: Concrete event class name to filter by.
        resource_type: Normalized audited resource family.
        resource_id: Text resource identifier.
        action: Normalized audited action.
        actor_user_id: Authenticated actor id.
        actor_username: Authenticated actor username.
        source: Event source that produced the audited event.
        occurred_from: Inclusive lower bound for event occurrence time.
        occurred_to: Inclusive upper bound for event occurrence time.
        created_from: Inclusive lower bound for audit persistence time.
        created_to: Inclusive upper bound for audit persistence time.

    Returns:
        Validated audit-log filter for the application query.

    Raises:
        TypeError: If a supplied value has an invalid runtime type.
        ValueError: If a string is blank, an identifier is invalid, or a
            datetime range is inconsistent.
    """
    return AuditLogFilter(
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        source=source,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        created_from=created_from,
        created_to=created_to,
    )


@audit_router.get("/", status_code=status.HTTP_200_OK)
def list_audits(
    query_bus: Annotated[QueryBus, Depends(get_authenticated_query_bus)],
    filters: Annotated[AuditLogFilter, Depends(get_audit_log_filter)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> AuditRecordPageResponse:
    """List audit records visible to the authenticated principal.

    Args:
        query_bus: Authenticated query bus injected by FastAPI.
        filters: Audit-log filters built from query parameters.
        limit: Maximum number of records to return.
        offset: Number of matching records to skip.
        include_total: Whether to include the total matching count.

    Returns:
        Paginated audit-record response.

    Raises:
        PermissionError: If the current principal cannot view the requested
            audit records.
        ValidationError: If pagination or audit filters are invalid.
        MessageHandlerNotFoundError: If the audit query is not registered.
        MessageTypeMismatchError: If query-bus registration is inconsistent.
        Exception: Propagates other failures raised by the registered query
            handler for the configured HTTP exception handlers.
    """
    query = AuditLogQuery(
        page=PageQuery(
            limit=limit,
            offset=offset,
            include_total=include_total,
        ),
        filters=filters,
    )

    result = query_bus.dispatch(key=VIEW_AUDITS, query=query)

    return AuditRecordPageResponse.from_page(result)
