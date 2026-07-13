"""Tests for event subscription composition."""

import unittest
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from src.adapters.driven.events.in_process_dispatcher import InProcessEventDispatcher
from src.adapters.driven.events.structured_event_logging_handler import StructuredEventLoggingHandler
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
from src.application.event_handlers.audit_event_handler import AuditEventHandler
from src.application.eventing.envelope import EventEnvelope
from src.application.events.reconciliation_events import RouteStateReconciled
from src.application.models.audit_log_query import AuditLogFilter
from src.application.models.audit_record import AuditRecord, AuditRecordDraft
from src.application.services.audit_mapping.mapper import AuditDescriptorMapper
from src.application.services.audit_mapping.packages import PACKAGE_AUDIT_MAPPINGS
from src.composition.event_subscriptions import build_eventing_components, register_event_subscriptions
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.events.package_events import PackageCreated
from src.domain.value_objects.location_code import LocationCode
from src.shared.event import Event

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
            initial_status=ItemStatus.TODO,
            initial_location=LocationCode("SYD"),
            expected_arrival=None,
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
        self.assertEqual(draft.event_version, 2)
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
                        initial_status=ItemStatus.TODO,
                        initial_location=LocationCode("SYD"),
                        expected_arrival=None,
                        occurred_at=NOW,
                    ),
                    source=EventSource.HTTP,
                    correlation_id=uuid4(),
                )
            )

        self.assertEqual(repository.drafts, [])

    def test_reconciliation_event_is_subscribed_to_audit_handler(self) -> None:
        repository = _AuditRepositorySpy()
        eventing = build_eventing_components(repository)

        eventing.publisher.publish(
            EventEnvelope(
                event=RouteStateReconciled(
                    route_id=30,
                    previous_status=RouteStatus.IN_PROGRESS,
                    new_status=RouteStatus.PLANNED,
                    departure_time=None,
                    expected_completion_time=None,
                    reason=RouteReconciliationReason.MISSING_DEPARTURE_TIME,
                    occurred_at=NOW,
                ),
                source=EventSource.HEARTBEAT,
                correlation_id=uuid4(),
            )
        )

        self.assertEqual(len(repository.drafts), 1)
        draft = repository.drafts[0]
        self.assertEqual(draft.event_type, "RouteStateReconciled")
        self.assertEqual(draft.resource_type, AuditResourceType.ROUTE)
        self.assertEqual(draft.resource_id, "30")
        self.assertEqual(draft.action, AuditAction.RECONCILED)

    def test_logging_subscription_does_not_depend_on_audit_mapping_coverage(self) -> None:
        repository = _AuditRepositorySpy()
        dispatcher = InProcessEventDispatcher()
        logging_handler = StructuredEventLoggingHandler()
        descriptor_mapper = AuditDescriptorMapper(PACKAGE_AUDIT_MAPPINGS)
        audit_handler = AuditEventHandler[Event](repository, descriptor_mapper)
        register_event_subscriptions(
            dispatcher,
            logging_handler,
            audit_handler,
            descriptor_mapper,
        )

        with self.assertLogs(
            "src.adapters.driven.events.structured_event_logging_handler",
            level="INFO",
        ) as captured:
            dispatcher.publish(
                EventEnvelope(
                    event=RouteStateReconciled(
                        route_id=30,
                        previous_status=RouteStatus.IN_PROGRESS,
                        new_status=RouteStatus.PLANNED,
                        departure_time=None,
                        expected_completion_time=None,
                        reason=RouteReconciliationReason.MISSING_DEPARTURE_TIME,
                        occurred_at=NOW,
                    ),
                    source=EventSource.HEARTBEAT,
                    correlation_id=uuid4(),
                )
            )

        self.assertIn("event_type=RouteStateReconciled", captured.output[0])
        self.assertEqual(repository.drafts, [])


if __name__ == "__main__":
    unittest.main()
