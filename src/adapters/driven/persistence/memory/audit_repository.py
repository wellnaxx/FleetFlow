"""In-memory audit repository implementation."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.application.models.audit_log_query import AuditLogFilter
from src.application.models.audit_record import AuditRecord, AuditRecordDraft

if TYPE_CHECKING:
    from uuid import UUID


class InMemoryAuditRepository:
    """Store immutable audit records in process memory.

    The repository preserves the same behavioral contract as durable audit
    adapters: ``event_id`` is an idempotency key, writes assign audit storage
    metadata, and read methods apply the audit filter model before returning
    records in newest-business-event order.
    """

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        """Initialize an empty audit repository.

        Args:
            clock: Optional persistence-time clock used to assign
                ``AuditRecord.created_at``. Defaults to current UTC time.
        """
        self._records_by_event_id: dict[UUID, AuditRecord] = {}
        self._next_id = 1
        self._clock = clock or (lambda: datetime.now(UTC))

    def add(self, draft: AuditRecordDraft) -> None:
        """Persist one audit draft unless its event was already stored.

        Args:
            draft: Audit data assembled by the audit event handler.
        """
        if draft.event_id in self._records_by_event_id:
            return

        record = self._build_record(draft)
        self._records_by_event_id[draft.event_id] = record
        self._next_id += 1

    def list_all(self, filters: AuditLogFilter) -> Sequence[AuditRecord]:
        """Return all audit records matching filters in stable descending order."""
        records = [record for record in self._records_by_event_id.values() if self._matches(record, filters)]
        records.sort(key=lambda record: (record.occurred_at, record.audit_id), reverse=True)
        return tuple(records)

    def list_page(self, filters: AuditLogFilter, limit: int, offset: int) -> Sequence[AuditRecord]:
        """Return a page of matching audit records."""
        return self.list_all(filters)[offset : offset + limit]

    def list_page_with_total(
        self,
        filters: AuditLogFilter,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[AuditRecord], int]:
        """Return a page of matching audit records and the full matching count."""
        records = self.list_all(filters)
        return records[offset : offset + limit], len(records)

    def _build_record(self, draft: AuditRecordDraft) -> AuditRecord:
        """Build a persisted audit record from a write-side draft."""
        return AuditRecord(
            audit_id=self._next_id,
            created_at=self._clock(),
            event_id=draft.event_id,
            event_type=draft.event_type,
            occurred_at=draft.occurred_at,
            recorded_at=draft.recorded_at,
            envelope_id=draft.envelope_id,
            correlation_id=draft.correlation_id,
            causation_id=draft.causation_id,
            source=draft.source,
            actor_user_id=draft.actor_user_id,
            actor_username=draft.actor_username,
            resource_type=draft.resource_type,
            resource_id=draft.resource_id,
            action=draft.action,
            payload_json=draft.payload_json,
        )

    def _matches(self, record: AuditRecord, filters: AuditLogFilter) -> bool:
        """Return whether a record satisfies all optional audit filters."""
        return (
            (filters.event_type is None or record.event_type == filters.event_type)
            and (filters.resource_type is None or record.resource_type == filters.resource_type)
            and (filters.resource_id is None or record.resource_id == filters.resource_id)
            and (filters.action is None or record.action == filters.action)
            and (filters.actor_user_id is None or record.actor_user_id == filters.actor_user_id)
            and (filters.actor_username is None or record.actor_username == filters.actor_username)
            and (filters.source is None or record.source == filters.source)
            and (filters.occurred_from is None or record.occurred_at >= filters.occurred_from)
            and (filters.occurred_to is None or record.occurred_at <= filters.occurred_to)
            and (filters.created_from is None or record.created_at >= filters.created_from)
            and (filters.created_to is None or record.created_at <= filters.created_to)
        )
