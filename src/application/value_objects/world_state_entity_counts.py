"""Value objects used by world-state application events."""

from dataclasses import dataclass

from src.shared.validation import require_non_negative_int


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
            try:
                require_non_negative_int(value, field_name)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name} must be a non-negative integer.") from exc
