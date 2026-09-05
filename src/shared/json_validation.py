"""Runtime validation for strict JSON-compatible object graphs."""

import math
from typing import cast

from src.shared.json_types import JSONObject


def require_json_object_keys(value: JSONObject, expected_keys: frozenset[str]) -> None:
    """Require a JSON object to contain exactly the specified keys.

    This checks field presence only. A key with a null value counts as present;
    callers validate individual values separately. Neither input is modified.

    Args:
        value: JSON object whose keys should be checked.
        expected_keys: Complete set of required keys, including nullable fields.

    Raises:
        ValueError: If unexpected or missing keys exist. Unexpected keys are
            reported first, and names within each error are sorted.
    """
    unexpected_keys = value.keys() - expected_keys
    if unexpected_keys:
        raise ValueError(f"Unexpected fields: {sorted(unexpected_keys)}")

    missing_keys = expected_keys - value.keys()
    if missing_keys:
        raise ValueError(f"Missing fields: {sorted(missing_keys)}")


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
