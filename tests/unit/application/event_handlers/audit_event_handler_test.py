"""Tests for audit event handling."""

import unittest
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.event_handlers.audit_event_handler import AuditEventHandler
from src.application.eventing.envelope import EventActor, EventEnvelope
from src.application.models.audit_log_query import AuditLogFilter
from src.application.models.audit_record import AuditRecord, AuditRecordDraft
from src.application.services.audit_mapping.registry import build_audit_descriptor_mapper
from src.domain.enums.item_status import ItemStatus
from src.domain.events.package_events import PackageCreated
from src.domain.value_objects.location_code import LocationCode
from src.shared.event import Event

NOW = datetime(2025, 1, 1, 12, 0)


class _AuditRepositorySpy:
    """Minimal repository spy for audit handler tests."""

    def __init__(self) -> None:
        self.drafts: list[AuditRecordDraft] = []

    def add(self, draft: AuditRecordDraft) -> None:
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


class AuditEventHandlerTests(unittest.TestCase):
    """Validate audit draft assembly from event envelopes."""

    def test_handle_persists_audit_draft_from_envelope_and_descriptor(self) -> None:
        repository = _AuditRepositorySpy()
        handler = AuditEventHandler[PackageCreated](repository, build_audit_descriptor_mapper())
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
        correlation_id = uuid4()
        causation_id = uuid4()
        envelope_id = uuid4()

        handler.handle(
            EventEnvelope(
                event=event,
                source=EventSource.CLI,
                correlation_id=correlation_id,
                causation_id=causation_id,
                envelope_id=envelope_id,
                actor=EventActor(user_id=1, username=" Manager "),
            )
        )

        self.assertEqual(len(repository.drafts), 1)
        draft = repository.drafts[0]
        self.assertEqual(draft.event_id, event.event_id)
        self.assertEqual(draft.event_version, 2)
        self.assertEqual(draft.event_type, "PackageCreated")
        self.assertEqual(draft.occurred_at, event.occurred_at)
        self.assertEqual(draft.recorded_at, event.recorded_at)
        self.assertEqual(draft.envelope_id, envelope_id)
        self.assertEqual(draft.correlation_id, correlation_id)
        self.assertEqual(draft.causation_id, causation_id)
        self.assertEqual(draft.source, EventSource.CLI)
        self.assertEqual(draft.actor_user_id, 1)
        self.assertEqual(draft.actor_username, "manager")
        self.assertEqual(draft.resource_type, AuditResourceType.PACKAGE)
        self.assertEqual(draft.resource_id, "20")
        self.assertEqual(draft.action, AuditAction.CREATED)
        self.assertEqual(
            draft.payload_json,
            {
                "package_id": "20",
                "customer_id": "10",
                "start_location": "SYD",
                "end_location": "MEL",
                "weight": 12.5,
                "initial_status": ItemStatus.TODO.value,
                "initial_location": "SYD",
                "expected_arrival": None,
            },
        )

    def test_handle_persists_none_actor_fields_when_envelope_has_no_actor(self) -> None:
        repository = _AuditRepositorySpy()
        handler = AuditEventHandler[PackageCreated](repository, build_audit_descriptor_mapper())

        handler.handle(
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
                source=EventSource.HEARTBEAT,
                correlation_id=uuid4(),
            )
        )

        draft = repository.drafts[0]
        self.assertIsNone(draft.actor_user_id)
        self.assertIsNone(draft.actor_username)

    def test_handle_does_not_persist_when_event_type_is_unsupported(self) -> None:
        repository = _AuditRepositorySpy()
        handler = AuditEventHandler[Event](repository, build_audit_descriptor_mapper())

        with self.assertRaisesRegex(ValueError, "Unsupported event type: Event"):
            handler.handle(
                EventEnvelope(
                    event=Event(occurred_at=NOW),
                    source=EventSource.SYSTEM,
                    correlation_id=uuid4(),
                )
            )

        self.assertEqual(repository.drafts, [])


if __name__ == "__main__":
    unittest.main()
