"""Value objects used by world-state application events."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorldStateEntityCounts:
    """Non-negative entity counts captured for a world-state snapshot."""

    customers: int
    packages: int
    routes: int
    trucks: int

    def __post_init__(self) -> None:
        """Validate that every snapshot entity count is a non-negative integer."""
        for field_name in ("customers", "packages", "routes", "trucks"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
