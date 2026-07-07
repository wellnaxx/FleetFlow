"""CLI command for viewing persisted audit-log records."""

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Final

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import (
    normalize_string,
    try_parse_datetime,
    try_parse_int,
)
from src.adapters.driving.cli.rendering.audit_record_renderer import render_audit_record
from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.application.models.audit_log_query import AuditLogFilter, AuditLogQuery
from src.application.use_cases.audit.view_audits import ViewAuditLogsUseCase
from src.application.use_cases.pagination import PageQuery

_ALLOWED_FILTER_OPTIONS: Final[frozenset[str]] = frozenset([
    "--limit",
    "--offset",
    "--total",
    "--event_type",
    "--resource_type",
    "--resource_id",
    "--action",
    "--actor_user_id",
    "--actor_username",
    "--source",
    "--occurred_from",
    "--occurred_to",
    "--created_from",
    "--created_to",
])

_FLAG_OPTIONS: Final[frozenset[str]] = frozenset([
    "--total",
])


class ViewAuditLogs(EventDrainingCommand[ViewAuditLogsUseCase]):
    """Render audit records using option-based CLI filters."""

    def execute(self) -> str:
        """Parse audit-log options, execute the use case, and render records.

        Returns:
            Multi-record audit-log output, or an empty-state message.

        Raises:
            PermissionError: If the current user is not allowed to view the
                requested audit records.
            ValueError: If CLI options or filter values are invalid.
        """
        query = _parse_query(self.params)
        result = self._run_and_drain(
            recorder=self.use_case,
            action=lambda: self.use_case.execute(query),
        )

        return (
            "\n\n".join(render_audit_record(record) for record in result.items)
            if result.items
            else "No audit records available."
        )


def _parse_query(params: Sequence[str]) -> AuditLogQuery:
    """Convert raw CLI option tokens into an audit-log query.

    Args:
        params: Raw command parameters after the command name.

    Returns:
        Typed audit-log query for the application use case.

    Raises:
        ValueError: If options are unknown, duplicated, missing values, or
            contain values that cannot be parsed into the target field type.
    """
    options: dict[str, str | None] = {}

    index = 0
    while index < len(params):
        token = params[index]

        if not token.startswith("--"):
            raise ValueError(f"Unexpected argument: {token}. Options must start with '--'.")

        if token not in _ALLOWED_FILTER_OPTIONS:
            raise ValueError(f"Unknown option: {token}")

        if token in options:
            raise ValueError(f"Duplicate option: {token}")

        if token in _FLAG_OPTIONS:
            options[token] = None
            index += 1
            continue

        if index + 1 >= len(params):
            raise ValueError(f"Missing value for {token}")

        value = params[index + 1]
        if value.startswith("--"):
            raise ValueError(f"Missing value for {token}")

        options[token] = value
        index += 2

    if "--total" in options and "--limit" not in options:
        raise ValueError("--total requires --limit.")

    limit_value = options.get("--limit")
    offset_value = options.get("--offset")

    return AuditLogQuery(
        page=PageQuery(
            limit=try_parse_int(limit_value, "--limit") if limit_value is not None else None,
            offset=try_parse_int(offset_value, "--offset") if offset_value is not None else 0,
            include_total="--total" in options,
        ),
        filters=AuditLogFilter(
            event_type=_get_optional_string(options, "--event_type"),
            resource_type=_get_optional_enum(options, "--resource_type", AuditResourceType),
            resource_id=_get_optional_string(options, "--resource_id"),
            action=_get_optional_enum(options, "--action", AuditAction),
            actor_user_id=_get_optional_int(options, "--actor_user_id"),
            actor_username=_get_optional_string(options, "--actor_username"),
            source=_get_optional_enum(options, "--source", EventSource),
            occurred_from=_get_optional_datetime(options, "--occurred_from"),
            occurred_to=_get_optional_datetime(options, "--occurred_to"),
            created_from=_get_optional_datetime(options, "--created_from"),
            created_to=_get_optional_datetime(options, "--created_to"),
        ),
    )


def _get_optional_string(options: dict[str, str | None], option: str) -> str | None:
    """Return a stripped option value without changing its case.

    Args:
        options: Parsed CLI option map.
        option: Option name to read.

    Returns:
        Stripped string value, or ``None`` when absent.

    Raises:
        ValueError: If the option is present but blank after stripping.
    """
    value = options.get(option)
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{option} must not be an empty string.")
    return normalized


def _get_optional_int(options: dict[str, str | None], option: str) -> int | None:
    """Parse an optional integer option."""
    value = options.get(option)
    if value is None:
        return None
    return try_parse_int(value, option)


def _get_optional_datetime(options: dict[str, str | None], option: str) -> datetime | None:
    """Parse an optional datetime option."""
    value = options.get(option)
    if value is None:
        return None
    return try_parse_datetime(value, option)


def _get_optional_enum[E: StrEnum](
    options: dict[str, str | None],
    option: str,
    enum_type: type[E],
) -> E | None:
    """Parse an optional enum option by enum value or enum member name.

    Args:
        options: Parsed CLI option map.
        option: Option name to read.
        enum_type: String enum type to parse.

    Returns:
        Parsed enum member, or ``None`` when absent.

    Raises:
        ValueError: If the supplied value is blank or not a supported enum
            value/name.
    """
    value = options.get(option)
    if value is None:
        return None

    normalized = normalize_string(value, option)

    for item in enum_type:
        if item.value.lower() == normalized or item.name.lower() == normalized:
            return item

    valid = ", ".join(item.value for item in enum_type)
    raise ValueError(f"{option} must be one of: {valid}.")
