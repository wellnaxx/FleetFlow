"""Layer-neutral parsing of JSON timestamp values into typed business time.

Parsing is separate from the validators that accept existing datetime objects.
These helpers preserve the accepted ISO forms and precision of
``datetime.fromisoformat``; they never convert timezones or strip offsets.
"""

from datetime import datetime

from src.shared.validation import require_naive_datetime, require_str


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
