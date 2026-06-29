"""Tests for audit-log query and filter models."""

import unittest
from datetime import datetime
from typing import Any, cast

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_log_query import AuditLogFilter, AuditLogQuery
from src.application.use_cases.pagination import PageQuery


class AuditLogFilterShould(unittest.TestCase):
    """Validate audit-log filter construction."""

    def test_accept_and_normalize_valid_filter_values(self) -> None:
        filters = AuditLogFilter(
            event_type=" PackageCreated ",
            resource_type=AuditResourceType.PACKAGE,
            resource_id=" 42 ",
            action=AuditAction.CREATED,
            actor_user_id=7,
            actor_username=" Admin ",
            source=EventSource.HTTP,
            occurred_from=datetime(2026, 1, 1, 12, 0),
            occurred_to=datetime(2026, 1, 1, 13, 0),
            created_from=datetime(2026, 1, 1, 14, 0),
            created_to=datetime(2026, 1, 1, 15, 0),
        )

        self.assertEqual(filters.event_type, "PackageCreated")
        self.assertEqual(filters.resource_id, "42")
        self.assertEqual(filters.actor_username, "Admin")

    def test_reject_empty_string_filters(self) -> None:
        with self.subTest(field_name="event_type"), self.assertRaises(ValueError):
            AuditLogFilter(event_type="   ")

        with self.subTest(field_name="resource_id"), self.assertRaises(ValueError):
            AuditLogFilter(resource_id="   ")

        with self.subTest(field_name="actor_username"), self.assertRaises(ValueError):
            AuditLogFilter(actor_username="   ")

    def test_reject_invalid_enum_filters(self) -> None:
        cases: tuple[tuple[str, object], ...] = (
            ("resource_type", "package"),
            ("action", "created"),
            ("source", "HTTP"),
        )

        for field_name, value in cases:
            with self.subTest(field_name=field_name), self.assertRaises(TypeError):
                kwargs: dict[str, Any] = {field_name: value}
                AuditLogFilter(**kwargs)

    def test_reject_invalid_actor_user_id(self) -> None:
        for value in (0, -1, True, "7"):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                AuditLogFilter(actor_user_id=cast(Any, value))

    def test_reject_invalid_datetime_filters(self) -> None:
        for field_name in ("occurred_from", "occurred_to", "created_from", "created_to"):
            with self.subTest(field_name=field_name), self.assertRaises(TypeError):
                AuditLogFilter(**{field_name: cast(Any, "not-a-datetime")})

    def test_reject_unordered_datetime_ranges(self) -> None:
        with self.assertRaisesRegex(ValueError, "occurred_from"):
            AuditLogFilter(
                occurred_from=datetime(2026, 1, 1, 13, 0),
                occurred_to=datetime(2026, 1, 1, 12, 0),
            )

        with self.assertRaisesRegex(ValueError, "created_from"):
            AuditLogFilter(
                created_from=datetime(2026, 1, 1, 13, 0),
                created_to=datetime(2026, 1, 1, 12, 0),
            )


class AuditLogQueryShould(unittest.TestCase):
    """Validate audit-log query construction."""

    def test_accept_page_and_filters(self) -> None:
        page = PageQuery(limit=25, offset=50, include_total=True)
        filters = AuditLogFilter(resource_type=AuditResourceType.PACKAGE)

        query = AuditLogQuery(page=page, filters=filters)

        self.assertIs(query.page, page)
        self.assertIs(query.filters, filters)
