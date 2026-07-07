"""HTTP response schemas for audit-log endpoints."""

from datetime import datetime

from pydantic import UUID4, BaseModel, NonNegativeInt, PositiveInt

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_record import AuditRecord
from src.application.use_cases.pagination import PageResult
from src.shared.json_types import JSONObject


class AuditRecordResponse(BaseModel):
    """Serialized audit record returned by the HTTP API."""

    audit_id: PositiveInt
    event_id: UUID4
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    envelope_id: UUID4
    correlation_id: UUID4
    causation_id: UUID4 | None = None
    source: EventSource
    actor_user_id: PositiveInt | None = None
    actor_username: str | None = None
    resource_type: AuditResourceType
    resource_id: str | None = None
    action: AuditAction
    payload_json: JSONObject
    created_at: datetime

    @classmethod
    def from_record(cls, record: AuditRecord) -> "AuditRecordResponse":
        """Build a response model from a persisted audit record.

        Args:
            record: Application audit record returned by a use case.

        Returns:
            HTTP response model containing the same audit data.
        """
        return cls(
            audit_id=record.audit_id,
            event_id=record.event_id,
            event_type=record.event_type,
            occurred_at=record.occurred_at,
            recorded_at=record.recorded_at,
            envelope_id=record.envelope_id,
            correlation_id=record.correlation_id,
            causation_id=record.causation_id,
            source=record.source,
            actor_user_id=record.actor_user_id,
            actor_username=record.actor_username,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            action=record.action,
            payload_json=record.payload_json,
            created_at=record.created_at,
        )


class AuditRecordPageResponse(BaseModel):
    """Paginated audit-record response."""

    items: list[AuditRecordResponse]
    total: NonNegativeInt | None = None
    count: NonNegativeInt
    limit: PositiveInt | None = None
    offset: NonNegativeInt

    @classmethod
    def from_page(cls, page: PageResult[AuditRecord]) -> "AuditRecordPageResponse":
        """Build a paginated response from a use-case page result.

        Args:
            page: Application page result containing audit records.

        Returns:
            HTTP page response with serialized audit-record items.
        """
        return cls(
            items=[AuditRecordResponse.from_record(record) for record in page.items],
            total=page.total,
            count=page.count,
            limit=page.limit,
            offset=page.offset,
        )
