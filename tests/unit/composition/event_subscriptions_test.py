"""Tests for event subscription composition."""

import unittest
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.eventing.envelope import EventEnvelope
from src.application.models.audit_log_query import AuditLogFilter
from src.application.models.audit_record import AuditRecord, AuditRecordDraft
from src.composition.event_subscriptions import build_eventing_components
from src.domain.events.package_events import PackageCreated
from src.domain.value_objects.location_code import LocationCode

NOW = datetime(2025, 1, 1, 12, 0)


class _AuditRepositorySpy:
    """Minimal audit repository spy for composition tests."""

    def __init__(self, *, fail_on_add: bool = False) -> None:
        self.fail_on_add = fail_on_add
        self.drafts: list[AuditRecordDraft] = []

    def add(self, draft: AuditRecordDraft) -> None:
        if self.fail_on_add:
            raise RuntimeError("audit repository unavailable")
        self.drafts.append(draft)

    def list_all(self, filters: AuditLogFilter) -> Sequence[AuditRecord]:
        return ()

    def list_page(self, filters: AuditLogFilter, limit: int, offset: int) -> Sequence[AuditRecord]:
        return ()

    def list_page_with_total(
        self,
        filters: AuditLogFilter,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[AuditRecord], int]:
        return (), 0


class EventSubscriptionsTests(unittest.TestCase):
    """Validate eventing composition wiring and strict failure policy."""

    def test_build_eventing_components_subscribes_audit_handler(self) -> None:
        repository = _AuditRepositorySpy()
        eventing = build_eventing_components(repository)
        event = PackageCreated(
            package_id=20,
            customer_id=10,
            start_location=LocationCode("SYD"),
            end_location=LocationCode("MEL"),
            weight=12.5,
            occurred_at=NOW,
        )

        eventing.publisher.publish(
            EventEnvelope(
                event=event,
                source=EventSource.CLI,
                correlation_id=uuid4(),
            )
        )

        self.assertEqual(len(repository.drafts), 1)
        draft = repository.drafts[0]
        self.assertEqual(draft.event_type, "PackageCreated")
        self.assertEqual(draft.resource_type, AuditResourceType.PACKAGE)
        self.assertEqual(draft.resource_id, "20")
        self.assertEqual(draft.action, AuditAction.CREATED)

    def test_audit_repository_failure_propagates_from_publish(self) -> None:
        repository = _AuditRepositorySpy(fail_on_add=True)
        eventing = build_eventing_components(repository)

        with self.assertRaisesRegex(RuntimeError, "audit repository unavailable"):
            eventing.publisher.publish(
                EventEnvelope(
                    event=PackageCreated(
                        package_id=20,
                        customer_id=10,
                        start_location=LocationCode("SYD"),
                        end_location=LocationCode("MEL"),
                        weight=12.5,
                        occurred_at=NOW,
                    ),
                    source=EventSource.HTTP,
                    correlation_id=uuid4(),
                )
            )

        self.assertEqual(repository.drafts, [])


if __name__ == "__main__":
    unittest.main()
