from dataclasses import dataclass


@dataclass(frozen=True)
class TruckReconciliationSummary:
    trucks_moved: int = 0
    trucks_released: int = 0
    state_changed: bool = False
