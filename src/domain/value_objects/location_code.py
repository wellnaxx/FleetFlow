"""Typed representation for supported location codes."""

from __future__ import annotations

from src.domain.exceptions import DomainValidationError


class LocationCode(str):
    """String-compatible domain type for route and truck location codes."""

    def __new__(cls, value: object) -> LocationCode:
        """Create a typed location code from a raw string.

        Args:
            value: Location code text.

        Returns:
            Typed location code.

        Raises:
            DomainValidationError: If the value is not a string.
            DomainValidationError: If the value is blank.
        """
        if not isinstance(value, str):
            raise DomainValidationError("Location code must be a string.")

        normalized = value.strip().upper()

        if not normalized:
            raise DomainValidationError("Location code cannot be blank.")

        return str.__new__(cls, normalized)


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
