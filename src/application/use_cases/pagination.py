"""Shared pagination validation for listing use cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageQuery:
    """Pagination request for list-style use cases."""

    limit: int | None = None
    offset: int = 0
    include_total: bool = False


@dataclass(frozen=True)
class PageResult[T]:
    """Paginated application result for list-style use cases."""

    items: tuple[T, ...]
    total: int | None
    limit: int | None
    offset: int

    @property
    def count(self) -> int:
        """Return the number of items in this result page."""
        return len(self.items)


def validate_unpaginated_offset(offset: int) -> None:
    """Validate the offset used for an unpaginated listing.

    Args:
        offset: Number of items requested to skip.

    Returns:
        None.

    Raises:
        ValueError: If an offset is provided without a page limit.
    """
    if offset != 0:
        raise ValueError("Offset cannot be used without a limit.")


def validate_page(limit: int, offset: int) -> None:
    """Validate bounded page arguments.

    Args:
        limit: Maximum number of items to return.
        offset: Number of items to skip.

    Returns:
        None.

    Raises:
        ValueError: If pagination arguments are out of range.
    """
    if limit < 1:
        raise ValueError("Limit must be greater than zero.")
    if offset < 0:
        raise ValueError("Offset must be greater than or equal to zero.")
