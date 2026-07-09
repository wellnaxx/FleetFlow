"""Tests for the Postgres audit repository adapter."""

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from psycopg.types.json import Jsonb

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.audit_repository import PostgresAuditRepository
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_log_query import AuditLogFilter
from src.application.models.audit_record import AuditRecordDraft

MODULE = "src.adapters.driven.persistence.database.repositories.audit_repository"
OCCURRED_AT = datetime(2025, 1, 1, 12, 0)
RECORDED_AT = datetime(2025, 1, 1, 12, 1, tzinfo=UTC)
CREATED_FROM = datetime(2025, 1, 2, 12, 0, tzinfo=UTC)
CREATED_TO = datetime(2025, 1, 3, 12, 0, tzinfo=UTC)


class PostgresAuditRepositoryTests(unittest.TestCase):
    """Validate audit repository SQL calls and result handling."""

    def setUp(self) -> None:
        self.repo = PostgresAuditRepository()

    @patch(f"{MODULE}.execute_write")
    def test_add_persists_draft_with_serialized_enum_values(self, execute_write_mock: MagicMock) -> None:
        draft = _draft()

        self.repo.add(draft)

        sql, params = execute_write_mock.call_args.args
        payload_param = params[-1]

        self.assertEqual(sql, QUERIES.audit.add)
        self.assertIsInstance(payload_param, Jsonb)
        assert isinstance(payload_param, Jsonb)
        self.assertEqual(payload_param.obj, {"package_id": "20"})
        execute_write_mock.assert_called_once_with(
            QUERIES.audit.add,
            (
                draft.event_id,
                "PackageCreated",
                OCCURRED_AT,
                RECORDED_AT,
                draft.envelope_id,
                draft.correlation_id,
                draft.causation_id,
                "CLI",
                10,
                "manager",
                "package",
                "20",
                "created",
                payload_param,
            ),
        )

    @patch(f"{MODULE}.fetch_all", return_value=[{"audit_id": 1}])
    @patch(f"{MODULE}.map_audit_record", return_value="record")
    def test_list_all_builds_full_where_clause(
        self,
        map_audit_record_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        filters = _full_filter()

        result = self.repo.list_all(filters)

        self.assertEqual(result, ["record"])
        sql, params = fetch_all_mock.call_args.args
        self.assertIn("WHERE event_type = %s", sql)
        self.assertIn("resource_type = %s", sql)
        self.assertIn("created_at <= %s", sql)
        self.assertEqual(
            params,
            (
                "PackageCreated",
                "package",
                "20",
                "created",
                10,
                "manager",
                "CLI",
                OCCURRED_AT - timedelta(minutes=1),
                OCCURRED_AT + timedelta(minutes=1),
                CREATED_FROM,
                CREATED_TO,
            ),
        )
        map_audit_record_mock.assert_called_once_with({"audit_id": 1})

    @patch(f"{MODULE}.fetch_all", return_value=[])
    def test_list_all_omits_where_clause_when_filters_are_empty(self, fetch_all_mock: MagicMock) -> None:
        self.repo.list_all(AuditLogFilter())

        sql, params = fetch_all_mock.call_args.args
        self.assertNotIn("WHERE", sql)
        self.assertEqual(params, ())

    @patch(f"{MODULE}.fetch_all", return_value=[{"audit_id": 1}])
    @patch(f"{MODULE}.map_audit_record", return_value="record")
    def test_list_page_appends_limit_and_offset_after_filter_params(
        self,
        map_audit_record_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        result = self.repo.list_page(
            AuditLogFilter(resource_type=AuditResourceType.PACKAGE),
            limit=5,
            offset=10,
        )

        self.assertEqual(result, ["record"])
        _, params = fetch_all_mock.call_args.args
        self.assertEqual(params, ("package", 5, 10))
        map_audit_record_mock.assert_called_once_with({"audit_id": 1})

    @patch(f"{MODULE}.fetch_all", return_value=[{"audit_id": 1, "total": 7}])
    @patch(f"{MODULE}.map_audit_record", return_value="record")
    def test_list_page_with_total_duplicates_filter_params_for_page_and_count(
        self,
        map_audit_record_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        result, total = self.repo.list_page_with_total(
            AuditLogFilter(source=EventSource.CLI),
            limit=5,
            offset=10,
        )

        self.assertEqual(result, ["record"])
        self.assertEqual(total, 7)
        _, params = fetch_all_mock.call_args.args
        self.assertEqual(params, ("CLI", 5, 10, "CLI"))
        map_audit_record_mock.assert_called_once_with({"audit_id": 1, "total": 7})

    @patch(f"{MODULE}.fetch_all", return_value=[{"audit_id": None, "total": 7}])
    @patch(f"{MODULE}.map_audit_record")
    def test_list_page_with_total_returns_empty_page_when_offset_exceeds_total(
        self,
        map_audit_record_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        result, total = self.repo.list_page_with_total(AuditLogFilter(), limit=5, offset=100)

        self.assertEqual(result, [])
        self.assertEqual(total, 7)
        fetch_all_mock.assert_called_once()
        map_audit_record_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_all", return_value=[{"audit_id": 1, "total": True}])
    def test_list_page_with_total_rejects_non_integer_total(self, fetch_all_mock: MagicMock) -> None:
        with self.assertRaisesRegex(TypeError, "Total count must be an integer."):
            self.repo.list_page_with_total(AuditLogFilter(), limit=5, offset=0)

        fetch_all_mock.assert_called_once()


def _draft() -> AuditRecordDraft:
    return AuditRecordDraft(
        event_id=uuid4(),
        event_type="PackageCreated",
        occurred_at=OCCURRED_AT,
        recorded_at=RECORDED_AT,
        envelope_id=uuid4(),
        correlation_id=uuid4(),
        causation_id=uuid4(),
        source=EventSource.CLI,
        actor_user_id=10,
        actor_username="manager",
        resource_type=AuditResourceType.PACKAGE,
        resource_id="20",
        action=AuditAction.CREATED,
        payload_json={"package_id": "20"},
    )


def _full_filter() -> AuditLogFilter:
    return AuditLogFilter(
        event_type="PackageCreated",
        resource_type=AuditResourceType.PACKAGE,
        resource_id="20",
        action=AuditAction.CREATED,
        actor_user_id=10,
        actor_username="manager",
        source=EventSource.CLI,
        occurred_from=OCCURRED_AT - timedelta(minutes=1),
        occurred_to=OCCURRED_AT + timedelta(minutes=1),
        created_from=CREATED_FROM,
        created_to=CREATED_TO,
    )


if __name__ == "__main__":
    unittest.main()
