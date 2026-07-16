"""Immutable validated paths for delivery routes."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Self, cast

from src.domain.exceptions import DomainValidationError
from src.domain.services.map import Map
from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True, slots=True)
class RoutePath:
    """Ordered, unique, and supported locations traversed by a route.

    Use :meth:`create` at raw-input boundaries to normalize strings into
    :class:`LocationCode` values. Direct construction accepts only an already
    normalized tuple and remains available for trusted internal callers.

    Attributes:
        locations: Canonical route locations in traversal order.
    """

    locations: tuple[LocationCode, ...]

    _pos_index: Mapping[LocationCode, int] = field(
        init=False,
        repr=False,
        compare=False,
    )

    @classmethod
    def create(cls, *locations: str | LocationCode) -> Self:
        """Normalize raw locations and construct a validated route path.

        Args:
            *locations: Ordered raw or typed location codes.

        Returns:
            Validated path containing canonical ``LocationCode`` values.

        Raises:
            DomainValidationError: If a location cannot be normalized or the
                resulting path violates a route-path invariant.
        """
        return cls(tuple(LocationCode(location) for location in locations))

    def __post_init__(self) -> None:
        """Validate route topology and build its immutable lookup index.

        Raises:
            DomainValidationError: If locations are not canonical location
                codes, fewer than two locations are supplied, a location is
                unsupported, or a location is repeated.
        """
        _require_location_tuple(self.locations)

        if len(self.locations) < 2:
            raise DomainValidationError("A route must have at least two locations.")

        valid_locations = set(Map.get_locations())
        invalid = next(
            (location for location in self.locations if location not in valid_locations),
            None,
        )
        if invalid is not None:
            raise DomainValidationError(f"Invalid location code: {invalid}.")

        if len(set(self.locations)) != len(self.locations):
            raise DomainValidationError("A route cannot contain duplicate locations.")

        object.__setattr__(
            self,
            "_pos_index",
            MappingProxyType({location: index for index, location in enumerate(self.locations)}),
        )

    @property
    def start(self) -> LocationCode:
        """Return the first location on the path."""
        return self.locations[0]

    @property
    def end(self) -> LocationCode:
        """Return the final location on the path."""
        return self.locations[-1]

    def includes_in_order(self, start: str | LocationCode, end: str | LocationCode) -> bool:
        """Return whether the route visits start before end.

        Args:
            start: Candidate raw or typed pickup location code.
            end: Candidate raw or typed delivery location code.

        Returns:
            True when both locations are present and start appears before end.

        Raises:
            DomainValidationError: If either argument cannot be normalized as
                a location code.
        """
        start_code = LocationCode(start)
        end_code = LocationCode(end)

        start_index = self._pos_index.get(start_code)
        end_index = self._pos_index.get(end_code)

        return start_index is not None and end_index is not None and start_index < end_index


def _require_location_tuple(value: object) -> None:
    """Require an immutable tuple containing only canonical location codes.

    Args:
        value: Runtime value supplied through the dataclass constructor.

    Raises:
        DomainValidationError: If the value is mutable or contains a value
            other than ``LocationCode``.
    """
    if not isinstance(value, tuple):
        raise DomainValidationError("Route path locations must be a tuple of LocationCode instances.")

    locations = cast(tuple[object, ...], value)
    if not all(isinstance(location, LocationCode) for location in locations):
        raise DomainValidationError("Route path locations must be a tuple of LocationCode instances.")
