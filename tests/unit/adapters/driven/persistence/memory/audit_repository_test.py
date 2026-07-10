"""Tests for the in-memory audit repository."""

import unittest
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.adapters.driven.persistence.memory.audit_repository import InMemoryAuditRepository
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_log_query import AuditLogFilter
from src.application.models.audit_record import AuditRecordDraft

CREATED_AT = datetime(2025, 1, 2, 12, 0, tzinfo=UTC)
RECORDED_AT = datetime(2025, 1, 1, 12, 1, tzinfo=UTC)
OCCURRED_AT = datetime(2025, 1, 1, 12, 0)


class InMemoryAuditRepositoryTests(unittest.TestCase):
    """Validate audit repository behavior independent of persistence indexes."""

    def test_add_assigns_storage_metadata_and_preserves_draft_fields(self) -> None:
        repo = InMemoryAuditRepository(clock=lambda: CREATED_AT)
        event_id = uuid4()
        envelope_id = uuid4()
        correlation_id = uuid4()
        causation_id = uuid4()
        draft = _draft(
            event_id=event_id,
            envelope_id=envelope_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        repo.add(draft)

        records = repo.list_all(AuditLogFilter())
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.audit_id, 1)
        self.assertEqual(record.created_at, CREATED_AT)
        self.assertEqual(record.event_id, event_id)
        self.assertEqual(record.event_version, 2)
        self.assertEqual(record.event_type, "PackageCreated")
        self.assertEqual(record.occurred_at, OCCURRED_AT)
        self.assertEqual(record.recorded_at, RECORDED_AT)
        self.assertEqual(record.envelope_id, envelope_id)
        self.assertEqual(record.correlation_id, correlation_id)
        self.assertEqual(record.causation_id, causation_id)
        self.assertEqual(record.source, EventSource.CLI)
        self.assertEqual(record.actor_user_id, 1)
        self.assertEqual(record.actor_username, "manager")
        self.assertEqual(record.resource_type, AuditResourceType.PACKAGE)
        self.assertEqual(record.resource_id, "20")
        self.assertEqual(record.action, AuditAction.CREATED)
        self.assertEqual(record.payload_json, {"package_id": "20"})

    def test_add_is_idempotent_by_event_id(self) -> None:
        repo = InMemoryAuditRepository(clock=lambda: CREATED_AT)
        event_id = uuid4()

        repo.add(_draft(event_id=event_id, resource_id="20"))
        repo.add(_draft(event_id=event_id, resource_id="21"))

        records = repo.list_all(AuditLogFilter())
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].audit_id, 1)
        self.assertEqual(records[0].resource_id, "20")

    def test_list_all_returns_records_by_occurred_at_then_audit_id_descending(self) -> None:
        repo = InMemoryAuditRepository(clock=lambda: CREATED_AT)
        first_time = OCCURRED_AT
        later_time = OCCURRED_AT + timedelta(hours=1)

        repo.add(_draft(event_id=uuid4(), resource_id="first", occurred_at=first_time))
        repo.add(_draft(event_id=uuid4(), resource_id="second", occurred_at=later_time))
        repo.add(_draft(event_id=uuid4(), resource_id="third", occurred_at=later_time))

        self.assertEqual(
            [record.resource_id for record in repo.list_all(AuditLogFilter())],
            ["third", "second", "first"],
        )

    def test_list_all_applies_exact_and_range_filters(self) -> None:
        repo = InMemoryAuditRepository(clock=lambda: CREATED_AT)
        matching = _draft(
            event_id=uuid4(),
            event_type="PackageCreated",
            occurred_at=OCCURRED_AT,
            source=EventSource.HTTP,
            actor_user_id=1,
            actor_username="manager",
            resource_type=AuditResourceType.PACKAGE,
            resource_id="20",
            action=AuditAction.CREATED,
        )
        repo.add(matching)
        repo.add(
            _draft(
                event_id=uuid4(),
                event_type="RouteCreated",
                occurred_at=OCCURRED_AT - timedelta(days=1),
                source=EventSource.CLI,
                actor_user_id=2,
                actor_username="employee",
                resource_type=AuditResourceType.ROUTE,
                resource_id="30",
                action=AuditAction.CREATED,
            )
        )

        records = repo.list_all(
            AuditLogFilter(
                event_type="PackageCreated",
                resource_type=AuditResourceType.PACKAGE,
                resource_id="20",
                action=AuditAction.CREATED,
                actor_user_id=1,
                actor_username="manager",
                source=EventSource.HTTP,
                occurred_from=OCCURRED_AT - timedelta(minutes=1),
                occurred_to=OCCURRED_AT + timedelta(minutes=1),
                created_from=CREATED_AT - timedelta(minutes=1),
                created_to=CREATED_AT + timedelta(minutes=1),
            )
        )

        self.assertEqual([record.event_id for record in records], [matching.event_id])

    def test_list_page_and_total_slice_matching_records(self) -> None:
        repo = InMemoryAuditRepository(clock=lambda: CREATED_AT)
        for index in range(4):
            repo.add(
                _draft(
                    event_id=uuid4(),
                    resource_id=str(index),
                    occurred_at=OCCURRED_AT + timedelta(minutes=index),
                )
            )

        page = repo.list_page(AuditLogFilter(), limit=2, offset=1)
        page_with_total, total = repo.list_page_with_total(AuditLogFilter(), limit=2, offset=1)

        self.assertEqual([record.resource_id for record in page], ["2", "1"])
        self.assertEqual([record.resource_id for record in page_with_total], ["2", "1"])
        self.assertEqual(total, 4)

    def test_list_page_returns_empty_when_offset_is_beyond_total(self) -> None:
        repo = InMemoryAuditRepository(clock=lambda: CREATED_AT)
        for index in range(2):
            repo.add(
                _draft(
                    event_id=uuid4(),
                    resource_id=str(index),
                    occurred_at=OCCURRED_AT + timedelta(minutes=index),
                )
            )

        page = repo.list_page(AuditLogFilter(), limit=2, offset=5)
        page_with_total, total = repo.list_page_with_total(AuditLogFilter(), limit=2, offset=5)

        self.assertEqual(page, ())
        self.assertEqual(page_with_total, ())
        self.assertEqual(total, 2)

    def test_list_page_returns_remaining_records_when_limit_exceeds_remaining(self) -> None:
        repo = InMemoryAuditRepository(clock=lambda: CREATED_AT)
        for index in range(3):
            repo.add(
                _draft(
                    event_id=uuid4(),
                    resource_id=str(index),
                    occurred_at=OCCURRED_AT + timedelta(minutes=index),
                )
            )

        page = repo.list_page(AuditLogFilter(), limit=10, offset=1)
        page_with_total, total = repo.list_page_with_total(AuditLogFilter(), limit=10, offset=1)

        self.assertEqual([record.resource_id for record in page], ["1", "0"])
        self.assertEqual([record.resource_id for record in page_with_total], ["1", "0"])
        self.assertEqual(total, 3)

    def test_list_page_applies_filters_before_pagination(self) -> None:
        repo = InMemoryAuditRepository(clock=lambda: CREATED_AT)
        for index in range(4):
            repo.add(
                _draft(
                    event_id=uuid4(),
                    resource_id=str(index),
                    resource_type=AuditResourceType.PACKAGE if index % 2 == 0 else AuditResourceType.ROUTE,
                    occurred_at=OCCURRED_AT + timedelta(minutes=index),
                )
            )

        filters = AuditLogFilter(resource_type=AuditResourceType.PACKAGE)
        page = repo.list_page(filters, limit=1, offset=1)
        page_with_total, total = repo.list_page_with_total(filters, limit=1, offset=1)

        self.assertEqual([record.resource_id for record in page], ["0"])
        self.assertEqual([record.resource_id for record in page_with_total], ["0"])
        self.assertEqual(total, 2)


def _draft(
    *,
    event_id: UUID,
    event_type: str = "PackageCreated",
    occurred_at: datetime = OCCURRED_AT,
    recorded_at: datetime = RECORDED_AT,
    envelope_id: UUID | None = None,
    correlation_id: UUID | None = None,
    causation_id: UUID | None = None,
    source: EventSource = EventSource.CLI,
    actor_user_id: int | None = 1,
    actor_username: str | None = "manager",
    resource_type: AuditResourceType = AuditResourceType.PACKAGE,
    resource_id: str | None = "20",
    action: AuditAction = AuditAction.CREATED,
) -> AuditRecordDraft:
    return AuditRecordDraft(
        event_id=event_id,
        event_version=2,
        event_type=event_type,
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        envelope_id=envelope_id or uuid4(),
        correlation_id=correlation_id or uuid4(),
        causation_id=causation_id,
        source=source,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        payload_json={"package_id": resource_id},
    )


if __name__ == "__main__":
    unittest.main()
