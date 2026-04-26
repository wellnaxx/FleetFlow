"""Serialization helpers for persisted naive datetime values."""

from datetime import UTC, datetime

ISO_FMT = "%Y-%m-%dT%H:%M:%S"


def dt_to_str(dt: datetime | None) -> str | None:
    """Serialize a datetime using second precision.

    FleetFlow stores route datetimes as timezone-naive strings. Domain code
    treats naive values as local wall-clock times. If an aware datetime reaches
    this persistence helper, it is converted to UTC and then stored without
    timezone metadata.

    Args:
        dt: Datetime to serialize.

    Returns:
        ISO-like string without microseconds, or `None`.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.strftime(ISO_FMT)


def dt_from_str(s: str | None) -> datetime | None:
    """Parse a persisted datetime string into a naive datetime.

    Args:
        s: Persisted datetime string.

    Returns:
        Parsed datetime, or None for blank values.

    Raises:
        ValueError: If the value is not in the persisted datetime format.
    """
    if not s:
        return None
    return datetime.strptime(s, ISO_FMT)
