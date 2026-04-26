"""Result model for truck reconciliation work within a heartbeat."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TruckReconciliationSummary:
    """Counts and change flag for one route's truck reconciliation."""

    trucks_moved: int = 0
    trucks_released: int = 0
    state_changed: bool = False
