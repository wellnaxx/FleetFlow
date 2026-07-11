"""Result model for truck reconciliation work within a heartbeat."""

from dataclasses import dataclass

from src.application.events.reconciliation_events import (
    TruckPositionReconciled,
    TruckRouteReferenceReconciled,
)
from src.domain.entities.truck import Truck


@dataclass(frozen=True, slots=True)
class TruckReconciliationSummary:
    """Summary of truck mutations produced while reconciling one route.

    Args:
        trucks_moved: Trucks whose location or transit target changed.
        trucks_released: Trucks released from completed routes.
        trucks_reconciled: Trucks whose missing route reference was repaired.
        events: Events describing direct truck-state corrections.
    """

    trucks_moved: tuple[Truck, ...] = ()
    trucks_released: tuple[Truck, ...] = ()
    trucks_reconciled: tuple[Truck, ...] = ()
    events: tuple[TruckPositionReconciled | TruckRouteReferenceReconciled, ...] = ()

    @property
    def state_changed(self) -> bool:
        """Return whether any truck state changed."""
        return bool(self.trucks_moved or self.trucks_released or self.trucks_reconciled)
