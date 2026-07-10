"""Postgres-backed audit repository implementation."""

from collections.abc import Sequence

from psycopg.types.json import Jsonb

from src.adapters.driven.persistence.database.executor import execute_write, fetch_all
from src.adapters.driven.persistence.database.mappers.audit import map_audit_record
from src.adapters.driven.persistence.database.queries import QUERIES
from src.application.models.audit_log_query import AuditLogFilter
from src.application.models.audit_record import AuditRecord, AuditRecordDraft
from src.ports.output.audit_repository import AuditRepositoryPort


class PostgresAuditRepository(AuditRepositoryPort):
    """Persist and query audit records from PostgreSQL.

    The repository keeps SQL query bodies in external files and builds only the
    optional ``WHERE`` clause in Python. Every user-provided value remains a
    bound parameter; only fixed repository-owned SQL fragments are formatted
    into the loaded query templates.
    """

    def add(self, draft: AuditRecordDraft) -> None:
        """Insert an audit draft, ignoring duplicates by event id.

        Args:
            draft: Audit record data assembled from an event envelope.

        Returns:
            None.

        Raises:
            DatabaseError: If the insert operation fails.
        """
        execute_write(
            QUERIES.audit.add,
            (
                draft.event_id,
                draft.event_version,
                draft.event_type,
                draft.occurred_at,
                draft.recorded_at,
                draft.envelope_id,
                draft.correlation_id,
                draft.causation_id,
                draft.source.value,
                draft.actor_user_id,
                draft.actor_username,
                draft.resource_type.value,
                draft.resource_id,
                draft.action.value,
                Jsonb(draft.payload_json),
            ),
        )

    def list_all(self, filters: AuditLogFilter) -> Sequence[AuditRecord]:
        """Return all audit records matching the supplied filters.

        Args:
            filters: Optional exact-match and timestamp-bound filters.

        Returns:
            Matching audit records ordered by ``occurred_at DESC, audit_id DESC``.
        """
        where_clause, params = self._build_where_clause(filters)

        audit_record_rows = fetch_all(QUERIES.audit.list_all.format(where_clause=where_clause), (*params,))

        return [map_audit_record(row) for row in audit_record_rows]

    def list_page(self, filters: AuditLogFilter, limit: int, offset: int) -> Sequence[AuditRecord]:
        """Return one page of audit records matching the supplied filters.

        Args:
            filters: Optional exact-match and timestamp-bound filters.
            limit: Maximum number of records to return.
            offset: Number of matching records to skip.

        Returns:
            Matching audit records in the requested page.
        """
        where_clause, params = self._build_where_clause(filters)

        audit_record_rows = fetch_all(
            QUERIES.audit.list_page.format(where_clause=where_clause),
            (*params, limit, offset),
        )

        return [map_audit_record(row) for row in audit_record_rows]

    def list_page_with_total(
        self,
        filters: AuditLogFilter,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[AuditRecord], int]:
        """Return one filtered audit page plus the total matching count.

        The underlying SQL includes the dynamic ``WHERE`` clause twice, once
        for the page CTE and once for the count CTE. Filter parameters are
        therefore passed twice, with ``limit`` and ``offset`` between them.

        Args:
            filters: Optional exact-match and timestamp-bound filters.
            limit: Maximum number of records to return.
            offset: Number of matching records to skip.

        Returns:
            Tuple of ``(records in requested page, total matching count)``.
        """
        where_clause, params = self._build_where_clause(filters)

        rows = fetch_all(
            QUERIES.audit.list_page_with_total.format(where_clause=where_clause),
            (*params, limit, offset, *params),
        )

        if not rows:
            return [], 0

        total_count = rows[0]["total"]
        if not isinstance(total_count, int) or isinstance(total_count, bool):
            raise TypeError("Total count must be an integer.")

        audit_record_rows = [row for row in rows if row["audit_id"] is not None]

        return [map_audit_record(row) for row in audit_record_rows], total_count

    def _build_where_clause(self, filters: AuditLogFilter) -> tuple[str, list[object]]:
        """Build a safe SQL ``WHERE`` fragment and matching parameter list.

        Args:
            filters: Audit filters already validated by ``AuditLogFilter``.

        Returns:
            Tuple containing the SQL fragment and bound parameters in the same
            order as their placeholders. The SQL fragment is either an empty
            string or starts with ``WHERE``.
        """
        conditions: list[str] = []
        params: list[object] = []

        if filters.event_type is not None:
            conditions.append("event_type = %s")
            params.append(filters.event_type)

        if filters.resource_type is not None:
            conditions.append("resource_type = %s")
            params.append(filters.resource_type.value)

        if filters.resource_id is not None:
            conditions.append("resource_id = %s")
            params.append(filters.resource_id)

        if filters.action is not None:
            conditions.append("action = %s")
            params.append(filters.action.value)

        if filters.actor_user_id is not None:
            conditions.append("actor_user_id = %s")
            params.append(filters.actor_user_id)

        if filters.actor_username is not None:
            conditions.append("actor_username = %s")
            params.append(filters.actor_username)

        if filters.source is not None:
            conditions.append("source = %s")
            params.append(filters.source.value)

        if filters.occurred_from is not None:
            conditions.append("occurred_at >= %s")
            params.append(filters.occurred_from)

        if filters.occurred_to is not None:
            conditions.append("occurred_at <= %s")
            params.append(filters.occurred_to)

        if filters.created_from is not None:
            conditions.append("created_at >= %s")
            params.append(filters.created_from)

        if filters.created_to is not None:
            conditions.append("created_at <= %s")
            params.append(filters.created_to)

        where_sql = ""
        if conditions:
            where_sql = "WHERE " + " AND ".join(conditions)

        return where_sql, params
