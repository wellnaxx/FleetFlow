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
        ValueError: If ``start`` is after ``end``.
    """
    if start is None or end is None:
        return

    if start > end:
        raise ValueError(f"{field_name}_from must be before or equal to {field_name}_to.")
