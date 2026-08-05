"""Routing key for the filtered audit-log query."""

from typing import Final

from src.application.messaging.query import QueryKey
from src.application.models.audit_log_query import AuditLogQuery
from src.application.models.audit_record import AuditRecord
from src.application.use_cases.pagination import PageResult

VIEW_AUDITS: Final[QueryKey[AuditLogQuery, PageResult[AuditRecord]]] = QueryKey(
    name="view_audits",
    query_type=AuditLogQuery,
)
