"""Result model for heartbeat reconciliation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HeartbeatSummary:
    """Counts of runtime changes made by one heartbeat pass."""

    routes_updated: int
    packages_updated: int
    trucks_moved: int
    trucks_released: int
    state_changed: bool
