"""Canonical normalization for persisted authentication identity fields."""

from src.domain.enums.auth import Role


def normalize_username(username: str | None) -> str:
    """Return a trimmed lowercase username or an empty string.

    Args:
        username: Raw username, or ``None``.

    Returns:
        Normalized username suitable for case-insensitive keys and lookups.
    """
    return (username or "").strip().lower()


def normalize_role(role: object) -> str:
    """Return the persisted value for a role enum or role string.

    Args:
        role: Runtime role enum or persisted role string.

    Returns:
        Canonical persisted role value.

    Raises:
        TypeError: If ``role`` is neither a role enum nor a string.
        ValueError: If a string does not identify a supported role.
    """
    if isinstance(role, Role):
        return role.value
    if not isinstance(role, str):
        raise TypeError(f"Invalid role: {role!r}")
    try:
        return Role(role.strip().upper()).value
    except ValueError as exc:
        raise ValueError(f"Invalid role: {role!r}") from exc
