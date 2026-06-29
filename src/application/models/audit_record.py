"""Audit-log records produced from serialized event envelopes.

Audit records are normalized, JSON-safe representations of published domain
and application events. Event-specific data is stored in ``payload_json`` after
serialization, while universal event and envelope metadata is stored in
dedicated columns.
"""

import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import cast
from uuid import UUID

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.event_sources import EventSource
from src.shared.json_types import JSONObject


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditRecordDraft:
    """Write-side audit record before persistence metadata is assigned.

    Event handlers build drafts from event envelopes after event-specific
    payload serialization. The draft contains the durable event identity,
    envelope context, normalized audit descriptor fields, and JSON-safe event
    details.

    Attributes:
        event_id: Unique id of the original domain or application event.
        event_type: Concrete event class name, e.g. ``PackageCreated``.
        occurred_at: Business timestamp carried by the event.
        recorded_at: Timestamp when FleetFlow recorded the event.
        envelope_id: Unique id of this publication envelope.
        correlation_id: Workflow/request id shared by related events.
        causation_id: Direct cause id, when one exists.
        source: Driving source that produced the event.
        actor_user_id: Authenticated actor id, when one exists.
        actor_username: Authenticated actor username, when one exists.
        resource_type: Normalized audited resource family.
        resource_id: Resource identifier normalized as text, when one exists.
        action: Normalized audited action.
        payload_json: Event-specific JSON-safe payload. Universal event and
            envelope metadata is stored in dedicated fields instead.
    """

    event_id: UUID
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    envelope_id: UUID
    correlation_id: UUID
    causation_id: UUID | None = None
    source: EventSource
    actor_user_id: int | None = None
    actor_username: str | None = None
    resource_type: AuditResourceType
    resource_id: str | None = None
    action: AuditAction
    payload_json: JSONObject

    def __post_init__(self) -> None:
        """Validate and normalize audit draft fields."""
        _require_uuid(self.event_id, "event_id")
        object.__setattr__(self, "event_type", _require_str(self.event_type, "event_type"))
        _require_datetime(self.occurred_at, "occurred_at")
        _require_datetime(self.recorded_at, "recorded_at")
        _require_uuid(self.envelope_id, "envelope_id")
        _require_uuid(self.correlation_id, "correlation_id")
        if self.causation_id is not None:
            _require_uuid(self.causation_id, "causation_id")
        _require_enum(self.source, "source", EventSource)
        if self.actor_user_id is not None:
            _require_positive_int(self.actor_user_id, "actor_user_id")
        if self.actor_username is not None:
            object.__setattr__(self, "actor_username", _require_str(self.actor_username, "actor_username"))
        _require_enum(self.resource_type, "resource_type", AuditResourceType)
        if self.resource_id is not None:
            object.__setattr__(self, "resource_id", _require_str(self.resource_id, "resource_id"))
        _require_enum(self.action, "action", AuditAction)
        object.__setattr__(self, "payload_json", _require_json_object(self.payload_json, "payload_json"))


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditRecord(AuditRecordDraft):
    """Persisted audit record with repository-assigned storage metadata.

    Attributes:
        audit_id: Positive repository-assigned audit-row identity.
        created_at: Timestamp when the audit record was persisted.
    """

    audit_id: int
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate draft fields and persisted audit metadata."""
        super().__post_init__()
        _require_positive_int(self.audit_id, "audit_id")
        _require_datetime(self.created_at, "created_at")


def _require_uuid(value: object, field_name: str) -> None:
    """Require a UUID value for an audit identity field.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Raises:
        TypeError: If ``value`` is not a UUID.
    """
    if not isinstance(value, UUID):
        raise TypeError(f"{field_name}: expected UUID, got {type(value).__name__}.")


def _require_str(value: object, field_name: str) -> str:
    """Require and return a non-empty stripped string.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        The stripped string value.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If ``value`` is empty after trimming whitespace.
    """
    if not isinstance(value, str):
        raise TypeError(f"{field_name}: expected str, got {type(value).__name__}.")

    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must be a non-empty string.")

    return normalized_value


def _require_datetime(value: object, field_name: str) -> None:
    """Require a datetime value for an audit timestamp field.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Raises:
        TypeError: If ``value`` is not a datetime.
    """
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name}: expected datetime, got {type(value).__name__}.")


def _require_enum(value: object, field_name: str, enum_class: type[StrEnum]) -> None:
    """Require a value that is an instance of the expected string enum.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.
        enum_class: Expected ``StrEnum`` subclass.

    Raises:
        TypeError: If ``value`` is not a member of ``enum_class``.
    """
    if not isinstance(value, enum_class):
        raise TypeError(f"{field_name}: expected {enum_class.__name__}, got {type(value).__name__}.")


def _require_positive_int(value: object, field_name: str) -> None:
    """Require an integer identity value greater than or equal to one.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Raises:
        TypeError: If ``value`` is not an int or is a bool.
        ValueError: If ``value`` is less than one.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name}: expected int, got {type(value).__name__}")

    if value < 1:
        raise ValueError(f"{field_name} must be a positive integer.")


def _require_json_object(value: object, field_name: str) -> JSONObject:
    """Validate and return a JSON object with string keys and JSON-compatible values.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        A shallow ``dict`` copy narrowed to ``JSONObject``.

    Raises:
        TypeError: If ``value`` is not a dict, has non-string keys, or contains
            values outside the JSON-compatible value set.
    """
    if not isinstance(value, dict):
        raise TypeError(f"{field_name}: expected JSON object, got {type(value).__name__}")

    json_object = cast(dict[object, object], value)
    _validate_json_object(json_object, field_name)
    return cast(JSONObject, dict(json_object))


def _validate_json_object(value: dict[object, object], field_name: str) -> None:
    """Validate a JSON object recursively.

    Args:
        value: Dictionary to validate as a JSON object.
        field_name: Field path used in error messages.

    Raises:
        TypeError: If any key is not a string or any nested value is not JSON-compatible.
    """
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{field_name}: expected JSON object keys as strings, got {type(key).__name__}")
        _validate_json_value(item, f"{field_name}.{key}")


def _validate_json_value(value: object, field_name: str) -> None:
    """Validate one JSON-compatible value recursively.

    Args:
        value: Runtime value to validate.
        field_name: Field path used in error messages.

    Raises:
        TypeError: If ``value`` is not JSON-compatible or is a non-finite float.
    """
    if value is None or isinstance(value, str | bool | int):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError(f"{field_name}: expected finite JSON number.")
        return

    if isinstance(value, list):
        items = cast(list[object], value)
        for index, item in enumerate(items):
            _validate_json_value(item, f"{field_name}[{index}]")
        return

    if isinstance(value, dict):
        json_object = cast(dict[object, object], value)
        _validate_json_object(json_object, field_name)
        return

    raise TypeError(f"{field_name} must contain only JSON-compatible values.")
