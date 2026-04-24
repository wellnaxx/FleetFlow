from dataclasses import dataclass


@dataclass(frozen=True)
class HeartbeatSummary:
    routes_updated: int
    packages_updated: int
    trucks_moved: int
    trucks_released: int
    state_changed: bool
