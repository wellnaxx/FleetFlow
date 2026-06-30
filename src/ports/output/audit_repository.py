"""Output port for durable audit-log storage adapters."""

from collections.abc import Sequence
from typing import Protocol

from src.application.models.audit_log_query import AuditLogFilter
from src.application.models.audit_record import AuditRecord, AuditRecordDraft


class AuditRepositoryPort(Protocol):
    """Persist and query immutable audit records.

    Audit repositories store normalized event-envelope records after event
    handlers serialize event-specific payloads into JSON-safe data. Write
    adapters accept drafts because storage metadata such as ``audit_id`` and
    ``created_at`` is assigned by the repository. Read adapters return fully
    persisted ``AuditRecord`` instances.
    """

    def add(self, draft: AuditRecordDraft) -> None:
        """Persist one audit record draft.

        Implementations should treat ``draft.event_id`` as an idempotency key
        so duplicate delivery of the same event does not create duplicate audit
        rows.

        Args:
            draft: Audit record data produced by an audit event handler.

        Returns:
            None.
        """
        ...

    def list_all(self, filters: AuditLogFilter) -> Sequence[AuditRecord]:
        """Return all audit records matching the supplied filters.

        Args:
            filters: Exact-match and timestamp-bound filters to apply.

        Returns:
            Matching audit records in repository-defined default order.
        """
        ...

    def list_page(self, filters: AuditLogFilter, limit: int, offset: int) -> Sequence[AuditRecord]:
        """Return a limited audit-record page matching the supplied filters.

        Args:
            filters: Exact-match and timestamp-bound filters to apply.
            limit: Maximum number of records to return.
            offset: Number of matching records to skip.

        Returns:
            Audit records in the requested page.
        """
        ...

    def list_page_with_total(
        self,
        filters: AuditLogFilter,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[AuditRecord], int]:
        """Return a filtered audit page and total matching count.

        Args:
            filters: Exact-match and timestamp-bound filters to apply.
            limit: Maximum number of records to return.
            offset: Number of matching records to skip.

        Returns:
            Tuple of ``(records in the requested page, total matching count)``.
        """
        ...
