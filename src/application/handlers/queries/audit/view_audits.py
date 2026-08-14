"""Query handler for authorized audit-log browsing."""

from src.application.models.audit_log_query import AuditLogQuery
from src.application.models.audit_record import AuditRecord
from src.application.use_cases.audit.view_audits import ViewAuditLogsUseCase
from src.application.use_cases.pagination import PageResult


class ViewAuditsQueryHandler:
    """Delegate the canonical audit query to the audit-log workflow."""

    def __init__(self, use_case: ViewAuditLogsUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Actor-scoped audit-log workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: AuditLogQuery) -> PageResult[AuditRecord]:
        """Return the audit records visible for the supplied query.

        Args:
            query: Pagination and filtering request to execute.

        Returns:
            Authorized page of persisted audit records.

        Raises:
            Exception: Propagates authorization, validation, persistence, and
                other failures raised by the use case.
        """
        return self._use_case.execute(query)
