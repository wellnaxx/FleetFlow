"""Tests for the audit-log view use case."""

import unittest
from collections.abc import Sequence
from datetime import datetime
from typing import cast
from uuid import UUID

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.event_sources import EventSource
from src.application.events.auth_events import AuthorizationDenied
from src.application.exceptions.application_errors import ValidationError
from src.application.models.audit_log_query import AuditLogFilter, AuditLogQuery
from src.application.models.audit_record import AuditRecord, AuditRecordDraft
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.audit.view_audits import ViewAuditLogsUseCase
from src.application.use_cases.pagination import PageQuery
from src.domain.enums.auth import Permission, Role
from tests.unit.application.use_cases.authz_helpers import employee_authz, manager_authz, principal


class ViewAuditLogsUseCaseShould(unittest.TestCase):
    """Verify audit-log authorization and pagination behavior."""

    def test_allow_manager_to_query_all_records_with_supplied_filters(self) -> None:
        record = make_audit_record(audit_id=1)
        repo = AuditRepositorySpy(records=(record,))
        filters = AuditLogFilter(actor_user_id=99)
        use_case = ViewAuditLogsUseCase(repo, manager_authz(), clock=fixed_clock)

        result = use_case.execute(AuditLogQuery(filters=filters))

        self.assertEqual(result.items, (record,))
        self.assertIsNone(result.total)
        self.assertEqual(repo.list_all_calls, [filters])
        self.assertEqual(use_case.pending_events, ())

    def test_allow_manager_to_query_page_without_total(self) -> None:
        record = make_audit_record(audit_id=1)
        repo = AuditRepositorySpy(records=(record,))
        filters = AuditLogFilter(resource_type=AuditResourceType.PACKAGE)
        query = AuditLogQuery(page=PageQuery(limit=5, offset=10), filters=filters)
        use_case = ViewAuditLogsUseCase(repo, manager_authz(), clock=fixed_clock)

        result = use_case.execute(query)

        self.assertEqual(result.items, (record,))
        self.assertIsNone(result.total)
        self.assertEqual(result.limit, 5)
        self.assertEqual(result.offset, 10)
        self.assertEqual(repo.list_page_calls, [(filters, 5, 10)])
        self.assertEqual(repo.list_page_with_total_calls, [])

    def test_allow_manager_to_query_page_with_total(self) -> None:
        record = make_audit_record(audit_id=1)
        repo = AuditRepositorySpy(records=(record,), total=12)
        filters = AuditLogFilter(action=AuditAction.CREATED)
        query = AuditLogQuery(page=PageQuery(limit=3, offset=6, include_total=True), filters=filters)
        use_case = ViewAuditLogsUseCase(repo, manager_authz(), clock=fixed_clock)

        result = use_case.execute(query)

        self.assertEqual(result.items, (record,))
        self.assertEqual(result.total, 12)
        self.assertEqual(repo.list_page_with_total_calls, [(filters, 3, 6)])
        self.assertEqual(repo.list_page_calls, [])

    def test_force_employee_queries_to_current_actor_id(self) -> None:
        record = make_audit_record(audit_id=1, actor_user_id=2, actor_username="employee")
        repo = AuditRepositorySpy(records=(record,))
        filters = AuditLogFilter(resource_type=AuditResourceType.PACKAGE)
        use_case = ViewAuditLogsUseCase(repo, employee_authz(), clock=fixed_clock)

        result = use_case.execute(AuditLogQuery(filters=filters))

        effective_filter = repo.list_all_calls[0]
        self.assertEqual(result.items, (record,))
        self.assertEqual(effective_filter.actor_user_id, 2)
        self.assertIsNone(effective_filter.actor_username)
        self.assertEqual(effective_filter.resource_type, AuditResourceType.PACKAGE)
        self.assertEqual(use_case.pending_events, ())

    def test_keep_employee_matching_actor_filters_and_force_actor_id(self) -> None:
        record = make_audit_record(audit_id=1, actor_user_id=2, actor_username="employee")
        repo = AuditRepositorySpy(records=(record,))
        filters = AuditLogFilter(actor_user_id=2, actor_username=" employee ")
        use_case = ViewAuditLogsUseCase(repo, employee_authz(), clock=fixed_clock)

        result = use_case.execute(AuditLogQuery(filters=filters))

        effective_filter = repo.list_all_calls[0]
        self.assertEqual(result.items, (record,))
        self.assertEqual(effective_filter.actor_user_id, 2)
        self.assertEqual(effective_filter.actor_username, "employee")

    def test_reject_employee_query_for_another_actor_id(self) -> None:
        repo = AuditRepositorySpy()
        use_case = ViewAuditLogsUseCase(repo, employee_authz(), clock=fixed_clock)
        query = AuditLogQuery(filters=AuditLogFilter(actor_user_id=99))

        with self.assertRaisesRegex(PermissionError, "Cannot view audit logs for other users"):
            use_case.execute(query)

        self.assertEqual(repo.list_all_calls, [])
        event = only_authorization_denied_event(use_case)
        self.assertIs(event.attempted_operation, AuthorizationOperation.AUDIT_LOG_VIEW)
        self.assertIs(event.target_resource_type, AuditResourceType.USER)
        self.assertEqual(event.target_resource_id, "99")
        self.assertEqual(event.required_permissions, (Permission.AUDIT_VIEW,))
        self.assertEqual(event.occurred_at, FIXED_NOW)

    def test_reject_employee_query_for_another_actor_username(self) -> None:
        repo = AuditRepositorySpy()
        use_case = ViewAuditLogsUseCase(repo, employee_authz(), clock=fixed_clock)
        query = AuditLogQuery(filters=AuditLogFilter(actor_username="manager"))

        with self.assertRaisesRegex(PermissionError, "Cannot view audit logs for other users"):
            use_case.execute(query)

        self.assertEqual(repo.list_all_calls, [])
        event = only_authorization_denied_event(use_case)
        self.assertIs(event.attempted_operation, AuthorizationOperation.AUDIT_LOG_VIEW)
        self.assertIs(event.target_resource_type, AuditResourceType.USER)
        self.assertEqual(event.target_resource_id, "manager")
        self.assertEqual(event.required_permissions, (Permission.AUDIT_VIEW,))

    def test_reject_unauthenticated_query(self) -> None:
        repo = AuditRepositorySpy()
        use_case = ViewAuditLogsUseCase(repo, AuthorizationService(None), clock=fixed_clock)

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(AuditLogQuery())

        self.assertEqual(repo.list_all_calls, [])
        event = only_authorization_denied_event(use_case)
        self.assertIs(event.attempted_operation, AuthorizationOperation.AUDIT_LOG_VIEW)
        self.assertIs(event.target_resource_type, AuditResourceType.AUDIT_LOG)
        self.assertIsNone(event.target_resource_id)
        self.assertEqual(event.required_permissions, (Permission.AUDIT_VIEW,))

    def test_reject_invalid_pagination_before_repository_query(self) -> None:
        repo = AuditRepositorySpy()
        use_case = ViewAuditLogsUseCase(repo, manager_authz(), clock=fixed_clock)

        with self.assertRaises(ValidationError):
            use_case.execute(AuditLogQuery(page=PageQuery(limit=0)))

        with self.assertRaises(ValidationError):
            use_case.execute(AuditLogQuery(page=PageQuery(limit=1, offset=-1)))

        with self.assertRaises(ValidationError):
            use_case.execute(AuditLogQuery(page=PageQuery(offset=1)))

        self.assertEqual(repo.list_all_calls, [])
        self.assertEqual(repo.list_page_calls, [])
        self.assertEqual(repo.list_page_with_total_calls, [])

    def test_principal_with_audit_view_permission_uses_unrestricted_path(self) -> None:
        auditor = principal(3, "auditor", Role.MANAGER)
        repo = AuditRepositorySpy()
        use_case = ViewAuditLogsUseCase(repo, AuthorizationService(auditor), clock=fixed_clock)
        filters = AuditLogFilter(actor_user_id=99)

        use_case.execute(AuditLogQuery(filters=filters))

        self.assertEqual(repo.list_all_calls, [filters])


class AuditRepositorySpy:
    """Small audit repository test double that records query calls."""

    def __init__(self, records: Sequence[AuditRecord] = (), total: int | None = None) -> None:
        self._records = tuple(records)
        self._total = len(self._records) if total is None else total
        self.list_all_calls: list[AuditLogFilter] = []
        self.list_page_calls: list[tuple[AuditLogFilter, int, int]] = []
        self.list_page_with_total_calls: list[tuple[AuditLogFilter, int, int]] = []

    def add(self, draft: AuditRecordDraft) -> None:
        """Store is not needed by these tests."""
        raise NotImplementedError

    def list_all(self, filters: AuditLogFilter) -> Sequence[AuditRecord]:
        """Return all configured records and capture the supplied filter."""
        self.list_all_calls.append(filters)
        return self._records

    def list_page(self, filters: AuditLogFilter, limit: int, offset: int) -> Sequence[AuditRecord]:
        """Return configured records and capture the page request."""
        self.list_page_calls.append((filters, limit, offset))
        return self._records

    def list_page_with_total(
        self,
        filters: AuditLogFilter,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[AuditRecord], int]:
        """Return configured records and total while capturing the page request."""
        self.list_page_with_total_calls.append((filters, limit, offset))
        return self._records, self._total


FIXED_NOW = datetime(2026, 1, 1, 12, 0)


def fixed_clock() -> datetime:
    """Return a stable business timestamp for recorded events."""
    return FIXED_NOW


def make_audit_record(
    *,
    audit_id: int,
    actor_user_id: int = 7,
    actor_username: str = "admin",
) -> AuditRecord:
    """Build a valid audit record for use-case tests."""
    return AuditRecord(
        event_id=UUID(f"11111111-1111-1111-1111-{audit_id:012d}"),
        event_version=2,
        event_type="PackageCreated",
        occurred_at=datetime(2026, 1, 1, 12, 0),
        recorded_at=datetime(2026, 1, 1, 12, 0, 1),
        envelope_id=UUID(f"22222222-2222-2222-2222-{audit_id:012d}"),
        correlation_id=UUID("33333333-3333-3333-3333-333333333333"),
        causation_id=None,
        source=EventSource.HTTP,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        resource_type=AuditResourceType.PACKAGE,
        resource_id=str(audit_id),
        action=AuditAction.CREATED,
        payload_json={"package_id": audit_id},
        audit_id=audit_id,
        created_at=datetime(2026, 1, 1, 12, 0, 2),
    )


def only_authorization_denied_event(use_case: ViewAuditLogsUseCase) -> AuthorizationDenied:
    """Return the single recorded authorization-denied event."""
    pending_events = use_case.pending_events
    assert len(pending_events) == 1
    return cast(AuthorizationDenied, pending_events[0])
