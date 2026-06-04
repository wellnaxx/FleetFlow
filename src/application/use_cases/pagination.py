"""Shared pagination validation for listing use cases."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from src.application.exceptions.application_errors import ValidationError


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
        ValidationError: If an offset is provided without a page limit.
    """
    if offset != 0:
        raise ValidationError("Offset cannot be used without a limit.")


def validate_page(limit: int, offset: int) -> None:
    """Validate bounded page arguments.

    Args:
        limit: Maximum number of items to return.
        offset: Number of items to skip.

    Returns:
        None.

    Raises:
        ValidationError: If pagination arguments are out of range.
    """
    if limit < 1:
        raise ValidationError("Limit must be greater than zero.")
    if offset < 0:
        raise ValidationError("Offset must be greater than or equal to zero.")


def execute_page_query[T](
    query: PageQuery,
    list_all: Callable[[], Sequence[T]],
    list_page: Callable[[int, int], Sequence[T]],
    list_page_with_total: Callable[[int, int], tuple[Sequence[T], int]],
) -> PageResult[T]:
    """Execute a standard page query against listing callables.

    Args:
        query: Pagination request to execute.
        list_all: Callable that returns the full unpaginated listing.
        list_page: Callable that returns a page without total count.
        list_page_with_total: Callable that returns a page and total count.

    Returns:
        Page result with immutable item storage.

    Raises:
        ValidationError: If pagination arguments are invalid.
    """
    if query.limit is None:
        validate_unpaginated_offset(query.offset)
        return PageResult(
            items=tuple(list_all()),
            total=None,
            limit=None,
            offset=query.offset,
        )

    validate_page(query.limit, query.offset)
    if query.include_total:
        items, total = list_page_with_total(query.limit, query.offset)
    else:
        items = list_page(query.limit, query.offset)
        total = None

    return PageResult(
        items=tuple(items),
        total=total,
        limit=query.limit,
        offset=query.offset,
    )
