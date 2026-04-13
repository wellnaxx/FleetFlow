from collections.abc import Sequence
from datetime import datetime


def validate_params_count(params: Sequence[str], min_count: int, max_count: int | None = None) -> None:
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
    if len(params) != expected_count:
        raise ValueError(
            f"Invalid number of arguments. Expected exactly {expected_count}; received: {len(params)}."
        )


def try_parse_int(s: str) -> int:
    try:
        return int(s)
    except (ValueError, TypeError) as err:
        raise ValueError("Invalid value for ID. Should be an integer.") from err


def try_parse_float(s: str) -> float:
    try:
        return float(s)
    except (ValueError, TypeError) as err:
        raise ValueError("Invalid value for weight. Should be a number.") from err


def parse_departure_from_tail(tokens: list[str]) -> tuple[list[str], datetime | None]:
    """
    If the tail of tokens contains a datetime, return (locations, dt).
    Supports:
      - ... <YYYY-MM-DD> <HH:MM>
      - ... "YYYY-MM-DD HH:MM"
    Otherwise returns (tokens, None).
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
