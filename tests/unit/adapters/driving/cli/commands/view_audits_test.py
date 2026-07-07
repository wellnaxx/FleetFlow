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
from src.application.use_cases.pagination import PageResult


class ViewAuditLogsShould(unittest.TestCase):
    """Verify audit-log CLI parsing, execution, and rendering behavior."""

    def make_cmd(self, params: list[str]) -> ViewAuditLogs:
        """Build a command with mocked use-case dependencies."""
        cmd = ViewAuditLogs.__new__(ViewAuditLogs)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_returns_empty_message_when_no_records_match(self) -> None:
        cmd = self.make_cmd([])
        cmd._use_case.execute.return_value = PageResult(items=(), total=None, limit=None, offset=0)  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "No audit records available.")
        cmd._event_collector.drain.assert_called_once_with((cmd._use_case,))  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_audits.render_audit_record")
    def test_execute_renders_records_separated_by_blank_lines(self, mock_render: MagicMock) -> None:
        cmd = self.make_cmd([])
        record_1 = MagicMock()
        record_2 = MagicMock()
        mock_render.side_effect = ["record one", "record two"]
        cmd._use_case.execute.return_value = PageResult(  # type: ignore[reportAttributeAccessIssue]
            items=(record_1, record_2),
            total=None,
            limit=None,
            offset=0,
        )

        result = cmd.execute()

        self.assertEqual(result, "record one\n\nrecord two")
        mock_render.assert_any_call(record_1)
        mock_render.assert_any_call(record_2)
        cmd._event_collector.drain.assert_called_once_with((cmd._use_case,))  # type: ignore[reportUnknownMemberType]

    def test_execute_builds_query_from_all_supported_options(self) -> None:
        cmd = self.make_cmd(
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
        cmd._use_case.execute.return_value = PageResult(items=(), total=0, limit=10, offset=5)  # type: ignore[reportAttributeAccessIssue]

        cmd.execute()

        query = cast(AuditLogQuery, cmd._use_case.execute.call_args.args[0])  # type: ignore[reportUnknownMemberType]
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
                cmd = self.make_cmd(params)

                with self.assertRaisesRegex(ValueError, expected_message):
                    cmd.execute()

                cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    def test_execute_rejects_blank_text_filters(self) -> None:
        cmd = self.make_cmd(["--resource_id", "   "])

        with self.assertRaisesRegex(ValueError, "--resource_id must not be an empty string"):
            cmd.execute()

        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    def test_execute_drains_use_case_events_when_use_case_raises(self) -> None:
        cmd = self.make_cmd([])
        cmd._use_case.execute.side_effect = PermissionError("Cannot view audit logs")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError):
            cmd.execute()

        cmd._event_collector.drain.assert_called_once_with((cmd._use_case,))  # type: ignore[reportUnknownMemberType]
