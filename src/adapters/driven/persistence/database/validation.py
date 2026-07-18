"""Validation helpers shared by Postgres repositories and graph loaders."""

from src.shared.validation import require_non_negative_int


def require_count(value: object, label: str) -> int:
    """Require a non-negative database count with repository-facing errors.

    Args:
        value: Raw count returned by a query.
        label: Human-readable count label used in errors.

    Returns:
        Validated non-negative count.

    Raises:
        TypeError: If ``value`` is not an integer or is a boolean.
        ValueError: If ``value`` is negative.
    """
    try:
        return require_non_negative_int(value, label)
    except TypeError as exc:
        raise TypeError(f"{label} must be an integer.") from exc
    except ValueError as exc:
        raise ValueError(f"{label} must be non-negative.") from exc
