"""Validation helpers shared by CLI command adapters."""

from collections.abc import Sequence
from datetime import datetime


def validate_params_count(params: Sequence[str], min_count: int, max_count: int | None = None) -> None:
    """Validate that a command received an allowed number of parameters.

    Args:
        params: Raw CLI parameters.
        min_count: Minimum accepted number of parameters.
        max_count: Maximum accepted number of parameters, or `None` for no
            upper bound.

    Raises:
        ValueError: If the parameter count is outside the allowed range.
    """
    count = len(params)
    if max_count is None:
        if count < min_count:
            raise ValueError(f"Invalid number of arguments. Expected at least {min_count}; received: {count}.")
    else:
        if count < min_count or count > max_count:
            raise ValueError(
                f"Invalid number of arguments. Expected between {min_count} and {max_count}; received: {count}."
            )


def validate_params_exact(params: Sequence[str], expected_count: int) -> None:
    """Validate that a command received exactly the expected parameter count.

    Args:
        params: Raw CLI parameters.
        expected_count: Required number of parameters.

    Raises:
        ValueError: If the count does not match.
    """
    if len(params) != expected_count:
        raise ValueError(
            f"Invalid number of arguments. Expected exactly {expected_count}; received: {len(params)}."
        )


def try_parse_int(s: str) -> int:
    """Parse an integer CLI value.

    Args:
        s: Raw CLI token.

    Returns:
        Parsed integer value.

    Raises:
        ValueError: If the token is not an integer.
    """
    try:
        return int(s)
    except (ValueError, TypeError) as err:
        raise ValueError("Invalid value for ID. Should be an integer.") from err


def try_parse_float(s: str) -> float:
    """Parse a floating-point CLI value.

    Args:
        s: Raw CLI token.

    Returns:
        Parsed floating-point value.

    Raises:
        ValueError: If the token is not numeric.
    """
    try:
        return float(s)
    except (ValueError, TypeError) as err:
        raise ValueError("Invalid value for weight. Should be a number.") from err


def parse_departure_from_tail(tokens: list[str]) -> tuple[list[str], datetime | None]:
    """Parse an optional departure datetime from the end of location tokens.

    Supports `... <YYYY-MM-DD> <HH:MM>` and quoted
    `... "YYYY-MM-DD HH:MM"` input forms.

    Args:
        tokens: Command tokens that may end with a datetime.

    Returns:
        A tuple of remaining location tokens and the parsed datetime, or `None`
        when no datetime is present.
    """
    if not tokens:
        return tokens, None

    if len(tokens) >= 2:
        date_part, time_part = tokens[-2], tokens[-1]
        try:
            dt = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M")
            return tokens[:-2], dt
        except ValueError:
            pass

    last = tokens[-1]
    for fmt in ("%Y-%m-%d %H:%M",):
        try:
            dt = datetime.strptime(last, fmt)
            return tokens[:-1], dt
        except ValueError:
            continue

    return tokens, None

def validate_passwords(new_pw: str, confirm: str) -> None:
    """Validate that the new password and confirmation match."""
    if new_pw != confirm:
        raise ValueError("Passwords do not match.")
