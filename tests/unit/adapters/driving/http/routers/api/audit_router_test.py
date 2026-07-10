"""Tests for audit HTTP routes."""

import unittest
from datetime import datetime
from typing import cast
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import audit_router as audit_router_module
from src.adapters.driving.http.routers.api.audit_router import audit_router
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_log_query import AuditLogQuery
from src.application.models.audit_record import AuditRecord
from src.application.use_cases.pagination import PageResult


class AuditRouterShould(unittest.TestCase):
    """Verify audit-log HTTP listing behavior."""

    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(audit_router)
        register_exception_handlers(self.app)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_audits_returns_paginated_records_and_builds_query(self) -> None:
        use_case = MagicMock()
        event_collector = MagicMock()
        record = make_audit_record()
        use_case.execute.return_value = PageResult(items=(record,), total=12, limit=1, offset=2)
        self.app.dependency_overrides[audit_router_module.get_view_audit_logs_use_case] = lambda: use_case
        self.app.dependency_overrides[audit_router_module.get_event_collector] = lambda: event_collector

        response = self.client.get(
            "/audit/",
            params={
                "limit": "1",
                "offset": "2",
                "include_total": "true",
                "event_type": "PackageCreated",
                "resource_type": "package",
                "resource_id": "42",
                "action": "created",
                "actor_user_id": "7",
                "actor_username": "alice",
                "source": "CLI",
                "occurred_from": "2026-01-01T12:00:00",
                "occurred_to": "2026-01-01T13:00:00",
                "created_from": "2026-01-01T12:00:02",
                "created_to": "2026-01-01T13:00:02",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 12)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["limit"], 1)
        self.assertEqual(body["offset"], 2)
        self.assertEqual(body["items"][0]["audit_id"], 1)
        self.assertEqual(body["items"][0]["event_version"], 2)
        self.assertEqual(body["items"][0]["event_type"], "PackageCreated")
        self.assertEqual(body["items"][0]["resource_type"], "package")
        self.assertEqual(body["items"][0]["action"], "created")
        self.assertEqual(body["items"][0]["payload_json"], {"package_id": 42})

        query = cast(AuditLogQuery, use_case.execute.call_args.args[0])
        self.assertEqual(query.page.limit, 1)
        self.assertEqual(query.page.offset, 2)
        self.assertTrue(query.page.include_total)
        self.assertEqual(query.filters.event_type, "PackageCreated")
        self.assertIs(query.filters.resource_type, AuditResourceType.PACKAGE)
        self.assertEqual(query.filters.resource_id, "42")
        self.assertIs(query.filters.action, AuditAction.CREATED)
        self.assertEqual(query.filters.actor_user_id, 7)
        self.assertEqual(query.filters.actor_username, "alice")
        self.assertIs(query.filters.source, EventSource.CLI)
        self.assertEqual(query.filters.occurred_from, datetime(2026, 1, 1, 12, 0))
        self.assertEqual(query.filters.occurred_to, datetime(2026, 1, 1, 13, 0))
        self.assertEqual(query.filters.created_from, datetime(2026, 1, 1, 12, 0, 2))
        self.assertEqual(query.filters.created_to, datetime(2026, 1, 1, 13, 0, 2))
        event_collector.drain.assert_called_once_with((use_case,))

    def test_list_audits_rejects_invalid_query_parameters(self) -> None:
        use_case = MagicMock()
        self.app.dependency_overrides[audit_router_module.get_view_audit_logs_use_case] = lambda: use_case

        response = self.client.get("/audit/?limit=0&actor_user_id=0&resource_type=unknown")

        self.assertEqual(response.status_code, 422)
        use_case.execute.assert_not_called()

    def test_list_audits_drains_events_when_permission_denied(self) -> None:
        use_case = MagicMock()
        event_collector = MagicMock()
        use_case.execute.side_effect = PermissionError("Cannot view audit logs for other users")
        self.app.dependency_overrides[audit_router_module.get_view_audit_logs_use_case] = lambda: use_case
        self.app.dependency_overrides[audit_router_module.get_event_collector] = lambda: event_collector

        response = self.client.get("/audit/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Cannot view audit logs for other users")
        event_collector.drain.assert_called_once_with((use_case,))


def make_audit_record() -> AuditRecord:
    """Build a valid audit record for HTTP response tests."""
    return AuditRecord(
        event_id=uuid4(),
        event_version=2,
        event_type="PackageCreated",
        occurred_at=datetime(2026, 1, 1, 12, 0),
        recorded_at=datetime(2026, 1, 1, 12, 0, 1),
        envelope_id=uuid4(),
        correlation_id=uuid4(),
        causation_id=None,
        source=EventSource.CLI,
        actor_user_id=7,
        actor_username="alice",
        resource_type=AuditResourceType.PACKAGE,
        resource_id="42",
        action=AuditAction.CREATED,
        payload_json={"package_id": 42},
        audit_id=1,
        created_at=datetime(2026, 1, 1, 12, 0, 2),
    )
