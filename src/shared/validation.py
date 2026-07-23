"""Layer-neutral runtime validation and primitive normalization helpers."""

import math
from datetime import datetime
from decimal import Decimal
from uuid import UUID


def require_int(value: object, field_name: str) -> int:
    """Require and return an integer, excluding booleans.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated integer.

    Raises:
        TypeError: If ``value`` is not an integer or is a boolean.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name}: expected int, got {type(value).__name__}")
    return value


def require_optional_int(value: object, field_name: str) -> int | None:
    """Require and return an integer or ``None``.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated integer or ``None``.

    Raises:
        TypeError: If ``value`` is neither an integer nor ``None``.
    """
    if value is None:
        return None
    try:
        return require_int(value, field_name)
    except TypeError as exc:
        raise TypeError(f"{field_name}: expected int or None, got {type(value).__name__}") from exc


def require_positive_int(value: object, field_name: str) -> int:
    """Require and return an integer greater than or equal to one.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated positive integer.

    Raises:
        TypeError: If ``value`` is not an integer or is a boolean.
        ValueError: If ``value`` is less than one.
    """
    normalized = require_int(value, field_name)
    if normalized < 1:
        raise ValueError(f"{field_name} must be a positive integer.")
    return normalized


def require_optional_positive_int(value: object, field_name: str) -> int | None:
    """Require and return a positive integer or ``None``.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated positive integer or ``None``.

    Raises:
        TypeError: If ``value`` is neither an integer nor ``None``.
        ValueError: If the supplied integer is less than one.
    """
    if value is None:
        return None
    return require_positive_int(value, field_name)


def require_non_negative_int(value: object, field_name: str) -> int:
    """Require and return an integer greater than or equal to zero.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated non-negative integer.

    Raises:
        TypeError: If ``value`` is not an integer or is a boolean.
        ValueError: If ``value`` is negative.
    """
    normalized = require_int(value, field_name)
    if normalized < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return normalized


def require_str(value: object, field_name: str) -> str:
    """Require and return a string without changing its contents.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated string.

    Raises:
        TypeError: If ``value`` is not a string.
    """
    if not isinstance(value, str):
        raise TypeError(f"{field_name}: expected str, got {type(value).__name__}")
    return value


def require_optional_str(value: object, field_name: str) -> str | None:
    """Require and return a string or ``None``.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated string or ``None``.

    Raises:
        TypeError: If ``value`` is neither a string nor ``None``.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name}: expected str or None, got {type(value).__name__}")
    return value


def require_non_empty_str(value: object, field_name: str) -> str:
    """Require and return a stripped, non-empty string.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Stripped non-empty string.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If ``value`` is empty after stripping whitespace.
    """
    normalized = require_str(value, field_name).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return normalized


def require_datetime(value: object, field_name: str) -> datetime:
    """Require and return a datetime.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated datetime.

    Raises:
        TypeError: If ``value`` is not a datetime.
    """
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name}: expected datetime, got {type(value).__name__}")
    return value


def require_optional_datetime(value: object, field_name: str) -> datetime | None:
    """Require and return a datetime or ``None``.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated datetime or ``None``.

    Raises:
        TypeError: If ``value`` is neither a datetime nor ``None``.
    """
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name}: expected datetime or None, got {type(value).__name__}")
    return value


def require_uuid(value: object, field_name: str) -> UUID:
    """Require and return a UUID.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated UUID.

    Raises:
        TypeError: If ``value`` is not a UUID.
    """
    if not isinstance(value, UUID):
        raise TypeError(f"{field_name}: expected UUID, got {type(value).__name__}")
    return value


def require_optional_uuid(value: object, field_name: str) -> UUID | None:
    """Require and return a UUID or ``None``.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated UUID or ``None``.

    Raises:
        TypeError: If ``value`` is neither a UUID nor ``None``.
    """
    if value is None:
        return None
    if not isinstance(value, UUID):
        raise TypeError(f"{field_name}: expected UUID or None, got {type(value).__name__}")
    return value


def _require_finite_float(value: object, field_name: str) -> float:
    """Require and normalize a finite integer or floating-point number."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{field_name}: expected int or float, got {type(value).__name__}")

    try:
        normalized = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field_name} must be finite.") from exc

    if not math.isfinite(normalized):
        raise ValueError(f"{field_name} must be finite.")
    return normalized


def require_non_negative_finite_float(value: object, field_name: str) -> float:
    """Require and normalize a finite number greater than or equal to zero.

    Integer and floating-point inputs are accepted, except booleans. Numeric
    strings and other coercible objects are deliberately rejected.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated value normalized to ``float``.

    Raises:
        TypeError: If ``value`` is not an integer or float, or is a boolean.
        ValueError: If ``value`` is non-finite or negative.
    """
    normalized = _require_finite_float(value, field_name)
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return normalized


def require_positive_finite_float(value: object, field_name: str) -> float:
    """Require and normalize a finite number greater than zero.

    Integer and floating-point inputs are accepted, except booleans. Numeric
    strings and other coercible objects are deliberately rejected.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated value normalized to ``float``.

    Raises:
        TypeError: If ``value`` is not an integer or float, or is a boolean.
        ValueError: If ``value`` is non-finite or not positive.
    """
    normalized = _require_finite_float(value, field_name)
    if normalized <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return normalized


def require_finite_decimal(value: object, field_name: str) -> Decimal:
    """Require and return a finite ``Decimal`` without coercion.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Original finite decimal value.

    Raises:
        TypeError: If ``value`` is not a ``Decimal``.
        ValueError: If ``value`` is NaN or positive/negative infinity.
    """
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name}: expected Decimal, got {type(value).__name__}")

    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite.")

    return value


def require_finite_positive_decimal(value: object, field_name: str) -> Decimal:
    """Require and return a finite ``Decimal`` greater than zero.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Original finite positive decimal value.

    Raises:
        TypeError: If ``value`` is not a ``Decimal``.
        ValueError: If ``value`` is non-finite, zero, or negative.
    """
    normalized = require_finite_decimal(value, field_name)

    if normalized <= 0:
        raise ValueError(f"{field_name} must be positive.")

    return normalized
