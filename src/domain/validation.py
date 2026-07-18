"""Domain validation adapters that translate primitive validation failures."""

from src.domain.exceptions import DomainValidationError
from src.shared.validation import (
    require_optional_positive_int as require_shared_optional_positive_int,
)
from src.shared.validation import require_positive_finite_float as require_shared_positive_finite_float
from src.shared.validation import require_positive_int as require_shared_positive_int


def require_positive_int(value: object, field_name: str) -> int:
    """Require a positive integer and translate failures to a domain error.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Raises:
        DomainValidationError: If ``value`` is not a positive integer.
    """
    try:
        return require_shared_positive_int(value, field_name)
    except (TypeError, ValueError) as exc:
        raise DomainValidationError(str(exc)) from exc


def require_optional_positive_int(value: object, field_name: str) -> int | None:
    """Require a positive integer or ``None`` and translate failures.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated positive integer or ``None``.

    Raises:
        DomainValidationError: If ``value`` is neither ``None`` nor a positive
            integer.
    """
    try:
        return require_shared_optional_positive_int(value, field_name)
    except (TypeError, ValueError) as exc:
        raise DomainValidationError(str(exc)) from exc


def require_positive_finite_float(value: object, field_name: str) -> float:
    """Require a positive finite number and translate failures.

    Args:
        value: Runtime value to validate.
        field_name: Field name used in the error message.

    Returns:
        Validated value normalized to ``float``.

    Raises:
        DomainValidationError: If ``value`` is not a positive finite number.
    """
    try:
        return require_shared_positive_finite_float(value, field_name)
    except (TypeError, ValueError) as exc:
        raise DomainValidationError(str(exc)) from exc
