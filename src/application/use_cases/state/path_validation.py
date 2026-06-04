"""Shared validation for world-state use-case paths."""

from src.application.exceptions.application_errors import ValidationError


def validate_world_state_path(path: str) -> str:
    """Validate and normalize a world-state snapshot path before persistence IO.

    Args:
        path: Candidate snapshot path.

    Returns:
        Stripped snapshot path.

    Raises:
        ValidationError: If the path is blank.
    """
    stripped_path = path.strip()
    if not stripped_path:
        raise ValidationError("World state snapshot path is required.")
    return stripped_path
