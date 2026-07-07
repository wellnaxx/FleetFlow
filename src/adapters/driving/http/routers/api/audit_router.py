"""HTTP routes for browsing audit-log records."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.driving.http.dependencies.eventing import execute_and_drain_events, get_event_collector
from src.adapters.driving.http.dependencies.use_cases import get_view_audit_logs_use_case
from src.adapters.driving.http.schemas.audit import AuditRecordPageResponse
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.eventing.collector import EventCollector
from src.application.models.audit_log_query import AuditLogFilter, AuditLogQuery
from src.application.use_cases.audit.view_audits import ViewAuditLogsUseCase
from src.application.use_cases.pagination import PageQuery

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
        Validated audit-log filter for the application use case.
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
    use_case: Annotated[ViewAuditLogsUseCase, Depends(get_view_audit_logs_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
    filters: Annotated[AuditLogFilter, Depends(get_audit_log_filter)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> AuditRecordPageResponse:
    """List audit records visible to the authenticated principal.

    Args:
        use_case: Audit-log view use case injected by FastAPI.
        event_collector: Collector used to publish authorization-denied events.
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
    """
    query = AuditLogQuery(
        page=PageQuery(
            limit=limit,
            offset=offset,
            include_total=include_total,
        ),
        filters=filters,
    )

    result = execute_and_drain_events(
        recorder=use_case, event_collector=event_collector, action=lambda: use_case.execute(query)
    )

    return AuditRecordPageResponse.from_page(result)
