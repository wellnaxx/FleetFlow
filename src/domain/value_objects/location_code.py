"""Typed representation for supported location codes."""
from __future__ import annotations


class LocationCode(str):
    """String-compatible domain type for route and truck location codes."""

    def __new__(cls, value: object) -> LocationCode:
        """Create a typed location code from a raw string.

        Args:
            value: Location code text.

        Returns:
            Typed location code.

        Raises:
            TypeError: If the value is not a string.
            ValueError: If the value is blank.
        """
        if not isinstance(value, str):
            raise TypeError("Location code must be a string.")

        text = value.strip().upper()
        if not text:
            raise ValueError("Location code cannot be blank.")
        return str.__new__(cls, text)


def location_code_or_none(value: str | LocationCode | None) -> LocationCode | None:
    """Convert an optional raw location value into a typed location code.

    Args:
        value: Raw string, typed location code, or `None`.

    Returns:
        Typed location code, or `None`.
    """
    if value is None:
        return None
    if isinstance(value, LocationCode):
        return value
    return LocationCode(value)
