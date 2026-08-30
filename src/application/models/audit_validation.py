"""Validation helpers specific to audit application models."""

from datetime import datetime

__all__ = (
    "require_ordered_optional_datetime_range",
)


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
