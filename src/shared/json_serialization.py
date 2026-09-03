"""Layer-neutral helpers for serializing typed values into JSON scalars.

These helpers perform small, deterministic conversions used by JSON-backed
projections and durable event payloads. They intentionally do not validate
domain meaning; callers remain responsible for supplying values that satisfy
their own model contracts.
"""

from datetime import datetime


def optional_str(value: object | None) -> str | None:
    """Serialize an optional value as a JSON string.

    Args:
        value: Value whose string representation should be serialized, or
            ``None`` when the JSON value should be null.

    Returns:
        ``str(value)`` when a value is present; otherwise ``None``.
    """
    return str(value) if value is not None else None


def optional_id(value: object | None) -> str | None:
    """Serialize an optional identifier without converting null to text.

    This semantic alias keeps identifier fields recognizable at mapping call
    sites while using the same representation as other optional stringified
    values.

    Args:
        value: Identifier to stringify, or ``None`` when absent.

    Returns:
        The identifier's string representation, or ``None``.
    """
    return optional_str(value)


def optional_isoformat(value: datetime | None) -> str | None:
    """Serialize an optional datetime in ISO 8601 format.

    The helper preserves the datetime's existing timezone information. It
    does not convert between naive, aware, app-local, or UTC time domains.

    Args:
        value: Datetime to serialize, or ``None`` when absent.

    Returns:
        The value returned by :meth:`datetime.isoformat`, or ``None``.
    """
    return value.isoformat() if value is not None else None
