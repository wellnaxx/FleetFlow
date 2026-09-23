"""Layer-neutral parsing of JSON strings into typed timestamps and enum members.

Parsing is separate from validation of already-typed objects. Timestamp helpers
preserve the accepted ISO forms and precision of ``datetime.fromisoformat``;
they never convert timezones or strip offsets. Enum helpers preserve exact wire
spelling and add field context to unknown-value and unknown-name errors.
"""

from datetime import datetime
from enum import Enum

from src.shared.validation import require_naive_datetime, require_str


def parse_enum_value[E: Enum](value: object, field_name: str, enum_class: type[E]) -> E:
    """Parse a string-valued enum member with payload-field error context.

    Args:
        value: JSON string containing an enum value, not a member name.
        field_name: Payload field or indexed path used in validation errors.
        enum_class: Concrete enum class whose values define the wire contract.

    Returns:
        The matching enum member, retaining its concrete type. Text is not
        stripped, case-normalized, or retried as a member name.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the enum rejects the value. The message identifies the
            field, enum class, and rejected text; the original error is chained.
    """
    text = require_str(value, field_name)
    try:
        return enum_class(text)
    except ValueError as exc:
        raise ValueError(f"{field_name}: unknown {enum_class.__name__} value {text!r}.") from exc


def parse_enum_name[E: Enum](value: object, field_name: str, enum_class: type[E]) -> E:
    """Parse an exact enum member name with payload-field error context.

    Args:
        value: JSON string containing a member name, such as a permission name.
        field_name: Payload field or indexed path used in validation errors.
        enum_class: Concrete enum class whose names define the wire contract.

    Returns:
        The named member, including declared aliases, retaining its concrete
        type. Values are never tried as a fallback, and text is not normalized.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the member name is unknown. The message identifies the
            field, enum class, and rejected text; the original ``KeyError`` is
            retained as the cause rather than escaping the payload boundary.
    """
    name = require_str(value, field_name)
    try:
        return enum_class[name]
    except KeyError as exc:
        raise ValueError(f"{field_name}: unknown {enum_class.__name__} name {name!r}.") from exc


def parse_naive_datetime(value: object, field_name: str) -> datetime:
    """Parse ISO text as a timezone-naive business timestamp.

    Args:
        value: JSON string containing an ISO-formatted datetime. Existing
            datetime objects, null, and other non-string values are rejected.
        field_name: Payload field name used in validation error messages.

    Returns:
        A naive datetime preserving the parsed time and microseconds. All naive
        forms accepted by ``datetime.fromisoformat`` remain supported, including
        date-only text, which represents midnight. Input is not stripped.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the text cannot be parsed or includes a timezone offset,
            including UTC (``Z`` or ``+00:00``). Parse errors retain their cause.
    """
    text = require_str(value, field_name)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name}: expected ISO-formatted datetime.") from exc
    return require_naive_datetime(parsed, field_name)


def parse_optional_naive_datetime(value: object, field_name: str) -> datetime | None:
    """Parse a nullable JSON business timestamp without coercing blank values.

    Args:
        value: ISO-formatted string, or ``None`` for JSON null. Empty strings
            are invalid, not an alternate representation of null.
        field_name: Payload field name used in validation error messages.

    Returns:
        ``None`` for null; otherwise the naive datetime returned by
        :func:`parse_naive_datetime` with the same accepted forms and precision.

    Raises:
        TypeError: If a non-null value is not a string.
        ValueError: If text is invalid or represents a timezone-aware datetime.
    """
    if value is None:
        return None
    return parse_naive_datetime(value, field_name)
