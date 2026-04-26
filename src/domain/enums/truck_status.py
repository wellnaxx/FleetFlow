"""Truck status constants."""

from typing import ClassVar


class TruckStatus:
    """Supported truck runtime statuses."""

    FREE: str = "Free"
    ON_THE_WAY: str = "On the way"
    STATUSES: ClassVar[list[str]] = [FREE, ON_THE_WAY]

    @classmethod
    def from_string(cls, s: str) -> str:
        """Normalize a user-facing truck status string.

        Args:
            s: Raw status string.

        Returns:
            Canonical truck status.

        Raises:
            ValueError: If the status is unknown.
        """
        s = s.strip().lower()
        if s in ("free", "available"):
            return cls.FREE
        if s in ("on_the_way", "busy", "on the way"):
            return cls.ON_THE_WAY
        raise ValueError("Invalid truck status")
