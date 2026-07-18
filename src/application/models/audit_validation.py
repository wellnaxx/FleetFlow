"""Validation helpers shared by audit application models."""

import math
from datetime import datetime
from enum import StrEnum
from typing import cast

from src.shared.json_types import JSONObject
from src.shared.validation import require_datetime, require_positive_int, require_uuid
from src.shared.validation import require_non_empty_str as require_str

__all__ = (
    "require_datetime",
    "require_enum",
    "require_json_object",
    "require_ordered_optional_datetime_range",
    "require_positive_int",
    "require_str",
    "require_uuid",
)


def require_enum(value: object, field_name: str, enum_class: type[StrEnum]) -> None:
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


def require_ordered_optional_datetime_range(
    start: datetime | None,
    end: datetime | None,
    field_name: str,
) -> None:
    """Require an optional datetime range to be ordered when both bounds exist.

    Args:
        start: Inclusive lower bound, or ``None`` when unbounded.
        end: Inclusive upper bound, or ``None`` when unbounded.
        field_name: Base field name used in the error message.

    Raises:
        ValueError: If both bounds exist and use different timezone awareness, or
            if ``start`` is after ``end``.
    """
    if start is None or end is None:
        return

    start_is_aware = start.tzinfo is not None and start.utcoffset() is not None
    end_is_aware = end.tzinfo is not None and end.utcoffset() is not None
    if start_is_aware != end_is_aware:
        raise ValueError(f"{field_name}_from and {field_name}_to must use the same timezone awareness.")

    if start > end:
        raise ValueError(f"{field_name}_from must be before or equal to {field_name}_to.")
    

def require_json_object(value: object, field_name: str) -> JSONObject:
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
