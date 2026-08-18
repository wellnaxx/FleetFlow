"""Tests for the audit-log CLI command."""

import unittest
from datetime import datetime
from typing import cast
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_audits import ViewAuditLogs
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_log_query import AuditLogQuery
from src.application.queries.audit.view_audits import VIEW_AUDITS
from src.application.use_cases.pagination import PageResult
from src.ports.input.query_bus import QueryBus


class ViewAuditLogsShould(unittest.TestCase):
    """Verify audit-log CLI parsing, execution, and rendering behavior."""

    def make_cmd(self, params: list[str]) -> tuple[ViewAuditLogs, MagicMock]:
        """Build a command with an isolated query-bus mock."""
        query_bus = MagicMock(spec=QueryBus)
        return ViewAuditLogs(params, query_bus), query_bus

    def test_execute_returns_empty_message_when_no_records_match(self) -> None:
        cmd, query_bus = self.make_cmd([])
        query_bus.dispatch.return_value = PageResult(items=(), total=None, limit=None, offset=0)

        result = cmd.execute()

        self.assertEqual(result, "No audit records available.")
        query_bus.dispatch.assert_called_once()

    @patch("src.adapters.driving.cli.commands.view_audits.render_audit_record")
    def test_execute_renders_records_separated_by_blank_lines(self, mock_render: MagicMock) -> None:
        cmd, query_bus = self.make_cmd([])
        record_1 = MagicMock()
        record_2 = MagicMock()
        mock_render.side_effect = ["record one", "record two"]
        query_bus.dispatch.return_value = PageResult(
            items=(record_1, record_2),
            total=None,
            limit=None,
            offset=0,
        )

        result = cmd.execute()

        self.assertEqual(result, "record one\n\nrecord two")
        mock_render.assert_any_call(record_1)
        mock_render.assert_any_call(record_2)
        query_bus.dispatch.assert_called_once()

    def test_execute_builds_query_from_all_supported_options(self) -> None:
        cmd, query_bus = self.make_cmd(
            [
                "--limit",
                "10",
                "--offset",
                "5",
                "--total",
                "--event_type",
                " PackageCreated ",
                "--resource_type",
                "PACKAGE",
                "--resource_id",
                " 42 ",
                "--action",
                "CREATED",
                "--actor_user_id",
                "7",
                "--actor_username",
                " Alice ",
                "--source",
                "cli",
                "--occurred_from",
                "2026-07-06T10:00:00",
                "--occurred_to",
                "2026-07-06 11:00",
                "--created_from",
                "2026-07-06",
                "--created_to",
                "2026-07-07",
            ]
        )
        query_bus.dispatch.return_value = PageResult(items=(), total=0, limit=10, offset=5)

        cmd.execute()

        query_bus.dispatch.assert_called_once()
        self.assertIs(query_bus.dispatch.call_args.kwargs["key"], VIEW_AUDITS)
        query = cast(AuditLogQuery, query_bus.dispatch.call_args.kwargs["query"])
        self.assertEqual(query.page.limit, 10)
        self.assertEqual(query.page.offset, 5)
        self.assertTrue(query.page.include_total)
        self.assertEqual(query.filters.event_type, "PackageCreated")
        self.assertIs(query.filters.resource_type, AuditResourceType.PACKAGE)
        self.assertEqual(query.filters.resource_id, "42")
        self.assertIs(query.filters.action, AuditAction.CREATED)
        self.assertEqual(query.filters.actor_user_id, 7)
        self.assertEqual(query.filters.actor_username, "Alice")
        self.assertIs(query.filters.source, EventSource.CLI)
        self.assertEqual(query.filters.occurred_from, datetime(2026, 7, 6, 10, 0))
        self.assertEqual(query.filters.occurred_to, datetime(2026, 7, 6, 11, 0))
        self.assertEqual(query.filters.created_from, datetime(2026, 7, 6))
        self.assertEqual(query.filters.created_to, datetime(2026, 7, 7))

    def test_execute_rejects_invalid_option_shapes(self) -> None:
        cases = (
            (["loose"], "Options must start"),
            (["--unknown"], "Unknown option"),
            (["--limit", "1", "--limit", "2"], "Duplicate option"),
            (["--limit"], "Missing value"),
            (["--limit", "--offset"], "Missing value"),
            (["--total"], "--total requires --limit"),
        )

        for params, expected_message in cases:
            with self.subTest(params=params):
                cmd, query_bus = self.make_cmd(params)

                with self.assertRaisesRegex(ValueError, expected_message):
                    cmd.execute()

                query_bus.dispatch.assert_not_called()

    def test_execute_rejects_blank_text_filters(self) -> None:
        cmd, query_bus = self.make_cmd(["--resource_id", "   "])

        with self.assertRaisesRegex(ValueError, "--resource_id must not be an empty string"):
            cmd.execute()

        query_bus.dispatch.assert_not_called()

    def test_execute_propagates_query_bus_failure(self) -> None:
        cmd, query_bus = self.make_cmd([])
        query_bus.dispatch.side_effect = PermissionError("Cannot view audit logs")

        with self.assertRaises(PermissionError):
            cmd.execute()

        query_bus.dispatch.assert_called_once()
