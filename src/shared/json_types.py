"""Shared type aliases for strict JSON-compatible data."""

# Scalar values allowed by JSON.
type JSONPrimitive = str | int | float | bool | None

# Any JSON-compatible value after event payload serialization.
type JSONValue = JSONPrimitive | list[JSONValue] | dict[str, JSONValue]

# Top-level event-specific JSON payload stored with an audit record.
type JSONObject = dict[str, JSONValue]
