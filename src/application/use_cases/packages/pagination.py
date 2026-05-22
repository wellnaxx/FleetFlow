"""Shared pagination validation for package listing use cases."""


def validate_pagination(limit: int | None, offset: int) -> bool:
    """Validate package page arguments and return whether a page was requested."""
    if limit is None:
        if offset != 0:
            raise ValueError("Offset cannot be used without a limit.")
        return False

    if limit < 1:
        raise ValueError("Limit must be greater than zero.")
    if offset < 0:
        raise ValueError("Offset must be greater than or equal to zero.")

    return True
